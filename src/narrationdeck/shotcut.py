from __future__ import annotations

import json
import hashlib
import os
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
    """Export a Shotcut-compatible MLT project file.
    
    Following MLT XML spec: https://mltframework.org/docs/mltxml/
    And Shotcut annotations: https://www.shotcut.org/notes/mltxml-annotations/
    """
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

    # Root element with Shotcut-specific attributes
    mlt = ET.Element("mlt", attrib={
        "LC_NUMERIC": "C",
        "version": "7.21.0",
        "producer": "main_bin",
    })
    
    # Profile (required by Shotcut)
    _add_profile(mlt, fps, width, height)

    # 1. Create all producers first (as per MLT rules)
    
    # Calculate fade duration
    fade_seconds = crossfade_seconds if crossfade_seconds > 0 else 0.0
    
    # Black background producer
    bg_producer = ET.SubElement(mlt, "producer", attrib={
        "id": "black",
        "in": "00:00:00.000",
        "out": _frames_to_time(length_frames, fps),
    })
    ET.SubElement(bg_producer, "property", attrib={"name": "resource"}).text = "0"
    ET.SubElement(bg_producer, "property", attrib={"name": "mlt_service"}).text = "color"
    ET.SubElement(bg_producer, "property", attrib={"name": "mlt_image_format"}).text = "rgba"
    ET.SubElement(bg_producer, "property", attrib={"name": "aspect_ratio"}).text = "1"
    
    # Build segment info for filter timing
    segment_durations = {}  # producer_id -> list of (duration_seconds, is_first, is_last)
    for idx, segment in enumerate(segments, start=1):
        image_id = segment["image_id"]
        start_time = float(segment["start"])
        end_time = float(segment["end"])
        duration = end_time - start_time
        is_first = (idx == 1)
        is_last = (idx == len(segments))
        
        producer_id = f"producer{idx}"
        segment_durations[producer_id] = {
            "duration": duration,
            "is_first": is_first,
            "is_last": is_last,
        }
    
    # Image producers with fade filters
    producer_map = {}  # image_id -> producer_id
    filter_id_counter = 0
    
    for idx, segment in enumerate(segments, start=1):
        image_id = segment["image_id"]
        if image_id in producer_map:
            continue  # Already created producer for this image
            
        image_path = _find_image_path(images_dir, image_id)
        if not image_path:
            continue
            
        producer_id = f"producer{idx}"
        producer_map[image_id] = producer_id
        
        # Use absolute path for resources
        abs_path = str(Path(image_path).resolve())
        
        # Get timing info for this segment
        seg_info = segment_durations.get(producer_id, {})
        duration = seg_info.get("duration", 5.0)
        is_first = seg_info.get("is_first", False)
        is_last = seg_info.get("is_last", False)
        
        producer = ET.SubElement(mlt, "producer", attrib={
            "id": producer_id,
            "in": "00:00:00.000",
            "out": _frames_to_time(length_frames, fps),
        })
        ET.SubElement(producer, "property", attrib={"name": "resource"}).text = abs_path
        ET.SubElement(producer, "property", attrib={"name": "mlt_service"}).text = "qimage"
        ET.SubElement(producer, "property", attrib={"name": "ttl"}).text = "1"
        # Shotcut hash for resource tracking
        file_hash = hashlib.md5(abs_path.encode()).hexdigest()
        ET.SubElement(producer, "property", attrib={"name": "shotcut:hash"}).text = file_hash
        
        # Add fade filters if crossfade is enabled
        if fade_seconds > 0:
            clip_out_time = _seconds_to_time(duration)
            
            # Fade In filter (brightness 0 -> 1)
            fade_in_end = min(fade_seconds, duration * 0.4)  # Don't exceed 40% of clip
            fade_in = ET.SubElement(producer, "filter", attrib={
                "id": f"filter{filter_id_counter}",
                "out": clip_out_time,
            })
            ET.SubElement(fade_in, "property", attrib={"name": "start"}).text = "1"
            ET.SubElement(fade_in, "property", attrib={"name": "level"}).text = f"00:00:00.000=0;{_seconds_to_time(fade_in_end)}=1"
            ET.SubElement(fade_in, "property", attrib={"name": "mlt_service"}).text = "brightness"
            ET.SubElement(fade_in, "property", attrib={"name": "shotcut:filter"}).text = "fadeInBrightness"
            ET.SubElement(fade_in, "property", attrib={"name": "alpha"}).text = "1"
            ET.SubElement(fade_in, "property", attrib={"name": "shotcut:animIn"}).text = _seconds_to_time(fade_in_end)
            filter_id_counter += 1
            
            # Fade Out filter (brightness 1 -> 0)
            fade_out_start = max(0, duration - fade_seconds)
            fade_out = ET.SubElement(producer, "filter", attrib={
                "id": f"filter{filter_id_counter}",
                "out": clip_out_time,
            })
            ET.SubElement(fade_out, "property", attrib={"name": "start"}).text = "1"
            ET.SubElement(fade_out, "property", attrib={"name": "level"}).text = f"{_seconds_to_time(fade_out_start)}=1;{clip_out_time}=0"
            ET.SubElement(fade_out, "property", attrib={"name": "mlt_service"}).text = "brightness"
            ET.SubElement(fade_out, "property", attrib={"name": "shotcut:filter"}).text = "fadeOutBrightness"
            ET.SubElement(fade_out, "property", attrib={"name": "alpha"}).text = "1"
            ET.SubElement(fade_out, "property", attrib={"name": "shotcut:animOut"}).text = _seconds_to_time(fade_seconds)
            filter_id_counter += 1
    
    # Audio producer
    audio_producer_id = None
    if audio_path and Path(audio_path).exists():
        audio_producer_id = "producer_audio"
        abs_audio_path = str(Path(audio_path).resolve())
        
        audio_producer = ET.SubElement(mlt, "producer", attrib={
            "id": audio_producer_id,
            "in": "00:00:00.000",
            "out": _frames_to_time(length_frames, fps),
        })
        ET.SubElement(audio_producer, "property", attrib={"name": "resource"}).text = abs_audio_path
        ET.SubElement(audio_producer, "property", attrib={"name": "mlt_service"}).text = "avformat"
        file_hash = hashlib.md5(abs_audio_path.encode()).hexdigest()
        ET.SubElement(audio_producer, "property", attrib={"name": "shotcut:hash"}).text = file_hash

    # 2. Create playlists (tracks)
    
    # Background playlist (required by Shotcut)
    bg_playlist = ET.SubElement(mlt, "playlist", attrib={"id": "background"})
    ET.SubElement(bg_playlist, "entry", attrib={
        "producer": "black",
        "in": "00:00:00.000",
        "out": _frames_to_time(length_frames - 1, fps),
    })
    
    # Video track playlist
    video_playlist = ET.SubElement(mlt, "playlist", attrib={"id": "playlist0"})
    ET.SubElement(video_playlist, "property", attrib={"name": "shotcut:video"}).text = "1"
    ET.SubElement(video_playlist, "property", attrib={"name": "shotcut:name"}).text = "V1"

    current_frame = 0
    for idx, segment in enumerate(segments, start=1):
        image_id = segment["image_id"]
        producer_id = producer_map.get(image_id)
        if not producer_id:
            continue
            
        start_time = float(segment["start"])
        end_time_seg = float(segment["end"])
        start_frame = int(round(start_time * fps))
        end_frame = int(round(end_time_seg * fps))
        duration_frames = max(1, end_frame - start_frame)

        # Insert blank if there's a gap
        if start_frame > current_frame:
            gap_frames = start_frame - current_frame
            ET.SubElement(video_playlist, "blank", attrib={
                "length": _frames_to_time(gap_frames, fps),
            })
            current_frame = start_frame

        # Add entry
        ET.SubElement(video_playlist, "entry", attrib={
            "producer": producer_id,
            "in": "00:00:00.000",
            "out": _frames_to_time(duration_frames - 1, fps),
        })
        current_frame += duration_frames
    
    # Audio track playlist
    audio_playlist = ET.SubElement(mlt, "playlist", attrib={"id": "playlist1"})
    ET.SubElement(audio_playlist, "property", attrib={"name": "shotcut:audio"}).text = "1"
    ET.SubElement(audio_playlist, "property", attrib={"name": "shotcut:name"}).text = "A1"
    
    if audio_producer_id:
        ET.SubElement(audio_playlist, "entry", attrib={
            "producer": audio_producer_id,
            "in": "00:00:00.000",
            "out": _frames_to_time(length_frames - 1, fps),
        })

    # 3. Main bin playlist (required by Shotcut before last tractor)
    main_bin = ET.SubElement(mlt, "playlist", attrib={"id": "main_bin"})
    ET.SubElement(main_bin, "property", attrib={"name": "xml_retain"}).text = "1"

    # 4. Main tractor with multitrack
    tractor = ET.SubElement(mlt, "tractor", attrib={
        "id": "main",
        "in": "00:00:00.000",
        "out": _frames_to_time(length_frames - 1, fps),
    })
    ET.SubElement(tractor, "property", attrib={"name": "shotcut"}).text = "1"
    ET.SubElement(tractor, "property", attrib={"name": "shotcut:projectAudioChannels"}).text = "2"
    
    # Multitrack wrapper (required by MLT spec)
    multitrack = ET.SubElement(tractor, "multitrack")
    ET.SubElement(multitrack, "track", attrib={"producer": "background"})
    ET.SubElement(multitrack, "track", attrib={"producer": "playlist0"})
    ET.SubElement(multitrack, "track", attrib={"producer": "playlist1", "hide": "video"})
    
    # Transitions for compositing
    trans_video = ET.SubElement(tractor, "transition", attrib={"id": "transition0"})
    ET.SubElement(trans_video, "property", attrib={"name": "a_track"}).text = "0"
    ET.SubElement(trans_video, "property", attrib={"name": "b_track"}).text = "1"
    ET.SubElement(trans_video, "property", attrib={"name": "mlt_service"}).text = "frei0r.cairoblend"
    ET.SubElement(trans_video, "property", attrib={"name": "always_active"}).text = "1"
    
    # Audio mix transition
    trans_audio = ET.SubElement(tractor, "transition", attrib={"id": "transition1"})
    ET.SubElement(trans_audio, "property", attrib={"name": "a_track"}).text = "0"
    ET.SubElement(trans_audio, "property", attrib={"name": "b_track"}).text = "2"
    ET.SubElement(trans_audio, "property", attrib={"name": "mlt_service"}).text = "mix"
    ET.SubElement(trans_audio, "property", attrib={"name": "sum"}).text = "1"

    # Pretty print XML
    xml_str = ET.tostring(mlt, encoding="unicode")
    import xml.dom.minidom
    parsed = xml.dom.minidom.parseString(xml_str)
    
    with open(mlt_path, "w", encoding="utf-8") as f:
        # Write XML declaration manually for proper encoding
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        # Write content without the extra declaration from toprettyxml
        lines = parsed.toprettyxml(indent="  ").split('\n')[1:]  # Skip first line (xml declaration)
        f.write('\n'.join(lines))
        
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

def _seconds_to_time(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm timecode format."""
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


