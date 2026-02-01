from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .constants import RESOLUTION_PRESETS


def build_resolve_payload(
    *,
    images_dir: str,
    resolution_label: str,
    frame_rate: str,
    project_mode: str,
    project_name: str,
    timeline_name: str,
    textplus_preset: str,
    image_map_text: str,
    last_generation: dict | None,
    allow_missing_image_anchors: bool,
) -> dict:
    resolution = _resolve_preset(resolution_label)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": {
            "mode": project_mode or "create",
            "name": project_name or _default_project_name(),
            "timeline_name": timeline_name or "NarrationDeck Timeline",
            "frame_rate": frame_rate,
            "resolution": resolution,
            "textplus_preset": textplus_preset or "",
        },
        "inputs": {
            "images_dir": images_dir,
            "image_anchor_text": image_map_text,
            "allow_missing_anchors": allow_missing_image_anchors,
        },
        "artifacts": {},
        "validation": {},
    }

    if last_generation:
        payload["artifacts"] = {
            "audio_path": last_generation.get("audio_path"),
            "srt_path": last_generation.get("srt_path"),
            "timestamps_path": last_generation.get("timestamps_path"),
            "image_timeline_path": last_generation.get("image_timeline_path"),
        }
    else:
        audio_files, srt_files = _detect_media_files(images_dir)
        warnings = []
        if len(audio_files) != 1:
            warnings.append(f"Expected 1 audio file, found {len(audio_files)}.")
        if len(srt_files) != 1:
            warnings.append(f"Expected 1 SRT file, found {len(srt_files)}.")
        if len(audio_files) == 1 and len(srt_files) == 1:
            payload["artifacts"] = {
                "audio_path": audio_files[0],
                "srt_path": srt_files[0],
                "timestamps_path": None,
                "image_timeline_path": None,
            }
        payload["validation"] = {
            "audio_files": audio_files,
            "srt_files": srt_files,
            "warnings": warnings,
        }

    return payload


def write_resolve_payload(images_dir: str, payload: dict) -> str:
    output_dir = Path(images_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"narrationdeck_payload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = output_dir / filename
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def _resolve_preset(label: str) -> dict:
    for preset in RESOLUTION_PRESETS:
        if label.endswith(preset["label"]) and label.startswith(preset["group"]):
            return {
                "group": preset["group"],
                "label": preset["label"],
                "width": preset["width"],
                "height": preset["height"],
            }
    return {"label": label, "width": None, "height": None}


def _default_project_name() -> str:
    return f"NarrationDeck_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _detect_media_files(images_dir: str) -> tuple[list[str], list[str]]:
    folder = Path(images_dir)
    if not folder.exists():
        return [], []
    audio_exts = {".mp3", ".wav", ".m4a", ".aac", ".flac"}
    audio_files = []
    srt_files = []
    for entry in folder.iterdir():
        if not entry.is_file():
            continue
        ext = entry.suffix.lower()
        if ext in audio_exts:
            audio_files.append(str(entry))
        elif ext == ".srt":
            srt_files.append(str(entry))
    return sorted(audio_files), sorted(srt_files)
