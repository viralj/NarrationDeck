from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from .constants import RESOLUTION_PRESETS


def export_shotcut_mlt(
    *,
    images_dir: str,
    image_timeline_path: str,
    audio_path: str | None,
    srt_path: str | None,
    frame_rate: str,
    resolution_label: str,
    output_prefix: str,
    crossfade_seconds: float = 0.0,
) -> str:
    output_dir = Path(images_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_prefix = _safe_prefix(output_prefix) or "narration"
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    mlt_path = output_dir / f"{safe_prefix}_{run_id}_shotcut.mlt"

    timeline_data = json.loads(Path(image_timeline_path).read_text(encoding="utf-8"))
    segments = timeline_data.get("segments", [])
    if not segments:
        raise ValueError("Image timeline has no segments.")

    fps = _parse_frame_rate(frame_rate)
    width, height = _resolve_dimensions(resolution_label)
    end_time = max(float(seg["end"]) for seg in segments)
    length_frames = max(1, int(round(end_time * fps)))

    # 1. Initialize Root
    mlt = ET.Element("mlt", attrib={
        "LC_NUMERIC": "C", 
        "version": "7.0.0", 
        "title": "Shotcut",
        "producer": "main_bin" # Matches test.mlt
    })
    _add_profile(mlt, fps, width, height)

    _add_color_producer(mlt, "background", length_frames)

    # 2. Detached Playlists
    video_playlist = ET.Element("playlist", attrib={"id": "videotrack0"})
    audio_playlist = ET.Element("playlist", attrib={"id": "audiotrack0"})
    background_playlist = ET.Element("playlist", attrib={"id": "background"})
    
    ET.SubElement(
        background_playlist,
        "entry",
        attrib={"producer": "background", "in": "0", "out": str(length_frames - 1)},
    )

    # 3. Producers & Video Playlist
    current_frame = 0
    crossfade_frames = max(0, int(round(crossfade_seconds * fps)))
    
    for idx, segment in enumerate(segments, start=1):
        image_id = segment["image_id"]
        image_path = _find_image_path(images_dir, image_id)
        if not image_path:
            continue
        
        # Calculate timing
        raw_start = float(segment["start"])
        raw_end = float(segment["end"])
        
        # Start frame logic (handling crossfade overlap)
        start_frame = int(round(raw_start * fps))
        if crossfade_frames > 0 and idx > 1:
            start_frame = max(0, start_frame - crossfade_frames)
            
        # End frame logic (original end point, maintained)
        end_frame = int(round(raw_end * fps))
        
        # Duration is the span from the (potentially shifted) start to the end
        duration_frames = max(1, end_frame - start_frame)
        
        producer_id = f"img_{idx:03d}"
        
        # Optimization: Set producer length to exactly what's needed plus a small buffer
        producer_length = duration_frames + 5
        _add_image_producer(mlt, producer_id, image_path, producer_length)

        # Handle gaps
        if start_frame > current_frame:
            gap = start_frame - current_frame
            ET.SubElement(video_playlist, "blank", attrib={"length": str(gap)})
            current_frame = start_frame

        ET.SubElement(
            video_playlist,
            "entry",
            attrib={
                "producer": producer_id,
                "in": "0",
                "out": str(duration_frames - 1),
            },
        )
        current_frame += duration_frames

    # 4. Audio
    if audio_path:
        audio_producer_id = "audio_main"
        _add_audio_producer(mlt, audio_producer_id, audio_path, length_frames)
        ET.SubElement(
            audio_playlist,
            "entry",
            attrib={"producer": audio_producer_id, "in": "0", "out": str(length_frames - 1)},
        )

    # 5. Bin Playlist (required structure seen in test.mlt, though we might not need to populate it fully)
    main_bin = ET.Element("playlist", attrib={"id": "main_bin"})
    ET.SubElement(main_bin, "property", attrib={"name": "xml_retain"}).text = "1"
    mlt.append(main_bin)

    # 6. Append Playlists
    mlt.append(background_playlist)
    mlt.append(video_playlist)
    mlt.append(audio_playlist)
    
    # 7. Tractor & Subtitles
    tractor = ET.SubElement(mlt, "tractor", attrib={
        "id": "tractor0", 
        "in": "0", 
        "out": str(length_frames - 1)
    })
    
    # Standard properties
    ET.SubElement(tractor, "property", attrib={"name": "shotcut"}).text = "1"
    
    # Tracks
    ET.SubElement(tractor, "track", attrib={"producer": "background"})
    ET.SubElement(tractor, "track", attrib={"producer": "videotrack0"})
    ET.SubElement(tractor, "track", attrib={"producer": "audiotrack0"})
    
    # Transitions (Mix) - simplified for V1/A1
    # V1 blend over background
    trans0 = ET.SubElement(tractor, "transition", attrib={"id": "transition0"})
    ET.SubElement(trans0, "property", attrib={"name": "a_track"}).text = "0"
    ET.SubElement(trans0, "property", attrib={"name": "b_track"}).text = "1"
    ET.SubElement(trans0, "property", attrib={"name": "mlt_service"}).text = "mix"
    ET.SubElement(trans0, "property", attrib={"name": "always_active"}).text = "1"
    
    # Audio mix
    trans1 = ET.SubElement(tractor, "transition", attrib={"id": "transition1"})
    ET.SubElement(trans1, "property", attrib={"name": "a_track"}).text = "0"
    ET.SubElement(trans1, "property", attrib={"name": "b_track"}).text = "2" # Audio track index
    ET.SubElement(trans1, "property", attrib={"name": "mlt_service"}).text = "mix"
    ET.SubElement(trans1, "property", attrib={"name": "always_active"}).text = "1"

    # Subtitles (Filter approach)
    if srt_path and Path(srt_path).exists():
        srt_content = Path(srt_path).read_text(encoding="utf-8")
        _add_subtitle_filters(tractor, srt_content, length_frames)

    # Write with pretty print
    xml_str = ET.tostring(mlt, encoding="utf-8")
    import xml.dom.minidom
    parsed = xml.dom.minidom.parseString(xml_str)
    
    with open(mlt_path, "w", encoding="utf-8") as f:
        f.write(parsed.toprettyxml(indent="  "))
        
    return str(mlt_path)

def _add_profile(mlt: ET.Element, fps: float, width: int, height: int):
    # Standard PAL/NTSC defaults often used by Shotcut, but we try to match requested
    ET.SubElement(
        mlt,
        "profile",
        attrib={
            "description": "automatic",
            "width": str(width),
            "height": str(height),
            "progressive": "1",
            "sample_aspect_num": "1",
            "sample_aspect_den": "1",
            "display_aspect_num": str(width),
            "display_aspect_den": str(height),
            "frame_rate_num": str(int(fps * 1000)),
            "frame_rate_den": "1000",
            "colorspace": "709",
        },
    )

def _add_color_producer(mlt: ET.Element, producer_id: str, length: int):
    producer = ET.SubElement(
        mlt, "producer", attrib={"id": producer_id, "in": "0", "out": str(length - 1)}
    )
    ET.SubElement(producer, "property", attrib={"name": "length"}).text = _frames_to_time(length)
    ET.SubElement(producer, "property", attrib={"name": "resource"}).text = "0"
    ET.SubElement(producer, "property", attrib={"name": "mlt_service"}).text = "color"
    ET.SubElement(producer, "property", attrib={"name": "mlt_image_format"}).text = "rgba"
    ET.SubElement(producer, "property", attrib={"name": "aspect_ratio"}).text = "1"

def _add_image_producer(mlt: ET.Element, producer_id: str, path: str, length: int):
    producer = ET.SubElement(
        mlt, "producer", attrib={"id": producer_id, "in": "0", "out": str(length - 1)}
    )
    ET.SubElement(producer, "property", attrib={"name": "length"}).text = _frames_to_time(length)
    ET.SubElement(producer, "property", attrib={"name": "resource"}).text = str(path)
    ET.SubElement(producer, "property", attrib={"name": "mlt_service"}).text = "qimage"
    ET.SubElement(producer, "property", attrib={"name": "aspect_ratio"}).text = "1"
    # Essential for preventing auto-conversion prompts in Shotcut
    ET.SubElement(producer, "property", attrib={"name": "shotcut:skipConvert"}).text = "1"

def _add_audio_producer(mlt: ET.Element, producer_id: str, path: str, length: int):
    producer = ET.SubElement(
        mlt, "producer", attrib={"id": producer_id, "in": "0", "out": str(length - 1)}
    )
    ET.SubElement(producer, "property", attrib={"name": "length"}).text = _frames_to_time(length)
    ET.SubElement(producer, "property", attrib={"name": "resource"}).text = str(path)
    # Using avformat-novalidate as seen in test.mlt
    ET.SubElement(producer, "property", attrib={"name": "mlt_service"}).text = "avformat-novalidate"
    ET.SubElement(producer, "property", attrib={"name": "shotcut:skipConvert"}).text = "1"

def _add_subtitle_filters(tractor: ET.Element, srt_content: str, length: int):
    # 1. The Feed Filter (holds the data)
    feed_filter = ET.SubElement(tractor, "filter", attrib={"id": "sub_feed"})
    ET.SubElement(feed_filter, "property", attrib={"name": "mlt_service"}).text = "subtitle_feed"
    ET.SubElement(feed_filter, "property", attrib={"name": "feed"}).text = "subtitle_track" # arbitrary name
    ET.SubElement(feed_filter, "property", attrib={"name": "lang"}).text = "eng"
    ET.SubElement(feed_filter, "property", attrib={"name": "shotcut:hidden"}).text = "1"
    ET.SubElement(feed_filter, "property", attrib={"name": "text"}).text = srt_content

    # 2. The Renderer Filter (displays the data)
    render_filter = ET.SubElement(tractor, "filter", attrib={"id": "sub_renderer", "out": str(length - 1)})
    ET.SubElement(render_filter, "property", attrib={"name": "mlt_service"}).text = "subtitle"
    ET.SubElement(render_filter, "property", attrib={"name": "feed"}).text = "subtitle_track" # Must match above
    
    # Styling properties (defaults roughly matching test.mlt)
    ET.SubElement(render_filter, "property", attrib={"name": "shotcut:filter"}).text = "subtitles"
    ET.SubElement(render_filter, "property", attrib={"name": "family"}).text = "Verdana"
    ET.SubElement(render_filter, "property", attrib={"name": "size"}).text = "36" # Reasonable default
    ET.SubElement(render_filter, "property", attrib={"name": "weight"}).text = "700"
    ET.SubElement(render_filter, "property", attrib={"name": "fgcolour"}).text = "#ffffffff"
    ET.SubElement(render_filter, "property", attrib={"name": "bgcolour"}).text = "#00000000"
    ET.SubElement(render_filter, "property", attrib={"name": "outline"}).text = "3"
    ET.SubElement(render_filter, "property", attrib={"name": "halign"}).text = "center"
    ET.SubElement(render_filter, "property", attrib={"name": "valign"}).text = "bottom"

def _add_shotcut_tractor(mlt: ET.Element, length: int):
    # Deprecated/Replaced by inline tractor construction in export_shotcut_mlt
    pass

def _frames_to_time(frames: int, fps: float = 25.0) -> str:
    # Proper hh:mm:ss.ms formatting if needed, but Shotcut often accepts frames or clock.
    # We'll use a simple approximation if strict clock is needed, or just let Shotcut handle it.
    # However, test.mlt uses clock format "00:00:00.000".
    # For simplicity, we stick to frames in XML attributes usually, but properties might need clock.
    # Let's implement a basic frame->clock converter.
    seconds = frames / fps
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    ms = int((s % 1) * 1000)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}.{ms:03d}"

def _parse_frame_rate(fps_str: str) -> float:
    try:
        return float(fps_str)
    except ValueError:
        return 30.0

def _safe_prefix(prefix: str) -> str:
    return "".join(c for c in prefix if c.isalnum() or c in ("-", "_")).strip()

def _resolve_dimensions(label: str) -> tuple[int, int]:
    # Basic lookup - extend as needed
    if "4k" in label.lower():
        return 3840, 2160
    if "1080" in label:
        return 1920, 1080
    if "720" in label:
        return 1280, 720
    return 1920, 1080 # Default

def _find_image_path(base_dir: str, image_id: str) -> str | None:
    # Simple search
    base = Path(base_dir)
    # 1. Try direct ID
    p = base / image_id
    if p.exists(): return str(p)
    # 2. Try with extensions
    for ext in [".png", ".jpg", ".jpeg", ".webp"]:
        p = base / f"{image_id}{ext}"
        if p.exists(): return str(p)
    return None

def _parse_srt(content: str) -> list[dict]:
    # Helper to parse SRT if we needed to split it, but now we dump raw content.
    # Kept for compatibility if needed elsewhere, or remove if unused.
    # For now, minimal implementation to satisfy imports if any.
    return []


