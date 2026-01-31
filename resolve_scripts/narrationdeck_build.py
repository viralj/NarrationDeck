import json
import os
import sys
from pathlib import Path


def _try_import_resolve():
    try:
        import DaVinciResolveScript as dvr
        return dvr
    except Exception:
        pass

    program_data = os.getenv("PROGRAMDATA")
    if program_data:
        module_path = Path(program_data) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Developer" / "Scripting" / "Modules"
        if module_path.exists():
            sys.path.append(str(module_path))
            try:
                import DaVinciResolveScript as dvr
                return dvr
            except Exception:
                return None
    return None


def _choose_payload_path():
    env_path = os.getenv("NARRATIONDECK_PAYLOAD")
    if env_path and Path(env_path).exists():
        return env_path

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        return filedialog.askopenfilename(
            title="Select NarrationDeck payload JSON",
            filetypes=[("JSON files", "*.json")],
        )
    except Exception:
        return ""


def _load_payload(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_frame_rate(value: str) -> float:
    value = str(value).strip()
    if value in {"23.976", "29.97", "59.94"}:
        mapping = {"23.976": 24000 / 1001, "29.97": 30000 / 1001, "59.94": 60000 / 1001}
        return mapping[value]
    try:
        return float(value)
    except Exception:
        return 30.0


def _find_image_path(images_dir: str, image_id: str):
    folder = Path(images_dir)
    if not folder.exists():
        return None
    prefix = f"{image_id}."
    for entry in sorted(folder.iterdir()):
        if entry.is_file() and entry.name.lower().startswith(prefix.lower()):
            return str(entry)
    return None


def _import_media_item(media_pool, path: str):
    items = media_pool.ImportMedia([path])
    if items and len(items) > 0:
        return items[0]
    return None


def main():
    dvr = _try_import_resolve()
    if not dvr:
        print("Could not import DaVinciResolveScript. Check Resolve Developer/Scripting modules.")
        return

    payload_path = _choose_payload_path()
    if not payload_path:
        print("No payload selected. Set NARRATIONDECK_PAYLOAD env var or choose a file.")
        return

    payload = _load_payload(payload_path)
    project_info = payload.get("project", {})
    inputs = payload.get("inputs", {})
    artifacts = payload.get("artifacts", {})

    resolve = dvr.scriptapp("Resolve")
    if not resolve:
        print("Resolve scripting app not available. Run this from Resolve Scripts menu.")
        return

    project_manager = resolve.GetProjectManager()
    project_name = project_info.get("name") or "NarrationDeck"
    project_mode = project_info.get("mode") or "create"

    project = None
    if project_mode == "existing":
        project = project_manager.LoadProject(project_name)
    else:
        project = project_manager.CreateProject(project_name)
        if not project:
            project = project_manager.LoadProject(project_name)

    if not project:
        print(f"Failed to open project: {project_name}")
        return

    frame_rate = _parse_frame_rate(project_info.get("frame_rate", "30"))
    resolution = project_info.get("resolution", {})
    width = resolution.get("width")
    height = resolution.get("height")

    if hasattr(project, "SetSetting"):
        project.SetSetting("timelineFrameRate", str(frame_rate))
        if width and height:
            project.SetSetting("timelineResolutionWidth", str(width))
            project.SetSetting("timelineResolutionHeight", str(height))

    media_pool = project.GetMediaPool()
    if not media_pool:
        print("MediaPool not available.")
        return

    timeline_name = project_info.get("timeline_name") or "NarrationDeck Timeline"
    timeline = media_pool.CreateEmptyTimeline(timeline_name)
    if not timeline:
        print("Failed to create timeline.")
        return

    if hasattr(timeline, "SetStartTimecode"):
        timeline.SetStartTimecode("00:00:00:00")

    image_timeline_path = artifacts.get("image_timeline_path")
    if not image_timeline_path or not Path(image_timeline_path).exists():
        print("Image timeline JSON not found. Generate it from the GUI first.")
        return

    with open(image_timeline_path, "r", encoding="utf-8") as handle:
        image_timeline = json.load(handle)
    segments = image_timeline.get("segments", [])
    if not segments:
        print("No image segments found.")
        return

    images_dir = inputs.get("images_dir") or ""
    images_dir = images_dir.strip()

    print(f"Importing {len(segments)} image segments...")
    for segment in segments:
        image_id = segment.get("image_id")
        if not image_id:
            continue
        image_path = _find_image_path(images_dir, image_id)
        if not image_path:
            print(f"Missing image for ID {image_id}")
            continue

        item = _import_media_item(media_pool, image_path)
        if not item:
            print(f"Failed to import image {image_path}")
            continue

        start = float(segment.get("start", 0))
        end = float(segment.get("end", start))
        duration_frames = max(1, int(round((end - start) * frame_rate)))
        record_frame = int(round(start * frame_rate))

        clip_info = {
            "mediaPoolItem": item,
            "startFrame": 0,
            "endFrame": max(0, duration_frames - 1),
            "recordFrame": record_frame,
            "mediaType": 1,
            "trackIndex": 1,
        }
        media_pool.AppendToTimeline([clip_info])

    audio_path = artifacts.get("audio_path")
    if audio_path and Path(audio_path).exists():
        audio_item = _import_media_item(media_pool, audio_path)
        if audio_item:
            clip_info = {
                "mediaPoolItem": audio_item,
                "startFrame": 0,
                "endFrame": 0,
                "recordFrame": 0,
                "mediaType": 2,
                "trackIndex": 1,
            }
            media_pool.AppendToTimeline([clip_info])

    print("NarrationDeck import complete.")


if __name__ == "__main__":
    main()
