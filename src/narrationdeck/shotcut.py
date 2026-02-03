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
    frame_rate: str,
    resolution_label: str,
    output_prefix: str,
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
    end_frame = max(1, int(round(end_time * fps)))

    mlt = ET.Element("mlt", attrib={"LC_NUMERIC": "C", "version": "7.0.0", "title": "Shotcut"})
    _add_profile(mlt, fps, width, height)

    _add_color_producer(mlt, "background", end_frame)

    video_playlist = ET.SubElement(mlt, "playlist", attrib={"id": "video_track"})
    audio_playlist = ET.SubElement(mlt, "playlist", attrib={"id": "audio_track"})
    background_playlist = ET.SubElement(mlt, "playlist", attrib={"id": "background"})
    ET.SubElement(background_playlist, "entry", attrib={"producer": "background", "in": "0", "out": str(end_frame)})

    current_frame = 0
    for idx, segment in enumerate(segments, start=1):
        image_id = segment["image_id"]
        image_path = _find_image_path(images_dir, image_id)
        if not image_path:
            continue
        producer_id = f"img_{idx:03d}"
        _add_image_producer(mlt, producer_id, image_path, end_frame)

        start = float(segment["start"])
        end = float(segment["end"])
        start_frame = int(round(start * fps))
        duration_frames = max(1, int(round((end - start) * fps)))
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

    if audio_path:
        audio_producer_id = "audio_main"
        _add_audio_producer(mlt, audio_producer_id, audio_path, end_frame)
        ET.SubElement(
            audio_playlist,
            "entry",
            attrib={"producer": audio_producer_id, "in": "0", "out": str(end_frame)},
        )

    _add_shotcut_tractor(mlt, end_frame)

    tree = ET.ElementTree(mlt)
    tree.write(mlt_path, encoding="utf-8", xml_declaration=True)
    return str(mlt_path)


def _add_profile(root: ET.Element, fps: float, width: int, height: int) -> None:
    fps_num, fps_den = _to_fraction(fps)
    aspect_num, aspect_den = _to_fraction(width / height)
    ET.SubElement(
        root,
        "profile",
        attrib={
            "description": "custom",
            "width": str(width),
            "height": str(height),
            "progressive": "1",
            "sample_aspect_num": "1",
            "sample_aspect_den": "1",
            "display_aspect_num": str(aspect_num),
            "display_aspect_den": str(aspect_den),
            "frame_rate_num": str(fps_num),
            "frame_rate_den": str(fps_den),
        },
    )


def _add_color_producer(root: ET.Element, producer_id: str, length_frames: int) -> None:
    producer = ET.SubElement(
        root,
        "producer",
        attrib={
            "id": producer_id,
            "in": "0",
            "out": str(length_frames),
        },
    )
    ET.SubElement(producer, "property", attrib={"name": "mlt_service"}).text = "color"
    ET.SubElement(producer, "property", attrib={"name": "resource"}).text = "black"
    ET.SubElement(producer, "property", attrib={"name": "length"}).text = str(length_frames)


def _add_image_producer(root: ET.Element, producer_id: str, path: str, length_frames: int) -> None:
    producer = ET.SubElement(
        root,
        "producer",
        attrib={"id": producer_id, "in": "0", "out": str(length_frames)},
    )
    ET.SubElement(producer, "property", attrib={"name": "mlt_service"}).text = "qimage"
    ET.SubElement(producer, "property", attrib={"name": "resource"}).text = path
    ET.SubElement(producer, "property", attrib={"name": "length"}).text = str(length_frames)


def _add_audio_producer(root: ET.Element, producer_id: str, path: str, length_frames: int) -> None:
    producer = ET.SubElement(
        root,
        "producer",
        attrib={"id": producer_id, "in": "0", "out": str(length_frames)},
    )
    ET.SubElement(producer, "property", attrib={"name": "mlt_service"}).text = "avformat"
    ET.SubElement(producer, "property", attrib={"name": "resource"}).text = path


def _add_shotcut_tractor(root: ET.Element, length_frames: int) -> None:
    tractor = ET.SubElement(
        root,
        "tractor",
        attrib={"id": "shotcut_project", "in": "0", "out": str(length_frames)},
    )
    ET.SubElement(tractor, "property", attrib={"name": "shotcut"}).text = "1"
    ET.SubElement(tractor, "property", attrib={"name": "shotcut:projectAudioChannels"}).text = "2"
    multitrack = ET.SubElement(tractor, "multitrack")
    ET.SubElement(multitrack, "track", attrib={"producer": "background"})
    ET.SubElement(multitrack, "track", attrib={"producer": "video_track"})
    ET.SubElement(multitrack, "track", attrib={"producer": "audio_track"})


def _find_image_path(images_dir: str, image_id: str) -> str | None:
    folder = Path(images_dir)
    prefix = f"{image_id}."
    for entry in sorted(folder.iterdir()):
        if entry.is_file() and entry.name.lower().startswith(prefix.lower()):
            return str(entry)
    return None


def _resolve_dimensions(label: str) -> tuple[int, int]:
    for preset in RESOLUTION_PRESETS:
        if label.endswith(preset["label"]) and label.startswith(preset["group"]):
            return preset["width"], preset["height"]
    return 1920, 1080


def _parse_frame_rate(value: str) -> float:
    if value in {"23.976", "29.97", "59.94"}:
        mapping = {"23.976": 24000 / 1001, "29.97": 30000 / 1001, "59.94": 60000 / 1001}
        return mapping[value]
    try:
        return float(value)
    except Exception:
        return 30.0


def _to_fraction(value: float) -> tuple[int, int]:
    if value == 0:
        return 0, 1
    den = 1000
    num = int(round(value * den))
    return num, den


def _safe_prefix(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum() or ch in ("-", "_")).strip()
