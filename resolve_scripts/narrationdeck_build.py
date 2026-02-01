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


def _seconds_to_timecode(seconds: float, frame_rate: float) -> str:
    if seconds < 0:
        seconds = 0.0
    total_frames = int(round(seconds * frame_rate))
    frames = total_frames % int(round(frame_rate))
    total_seconds = total_frames // int(round(frame_rate))
    secs = total_seconds % 60
    total_minutes = total_seconds // 60
    mins = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours:02d}:{mins:02d}:{secs:02d}:{frames:02d}"


def _set_title_text(title_item, text: str) -> bool:
    try:
        comp = title_item.GetFusionCompByIndex(1)
    except Exception:
        comp = None
    if not comp:
        return False

    try:
        text_tools = comp.GetToolList(False, "TextPlus")
    except Exception:
        text_tools = None

    if text_tools:
        for tool in text_tools.values():
            try:
                tool.SetInput("StyledText", text)
                return True
            except Exception:
                continue

    try:
        tool_list = comp.GetToolList(False)
    except Exception:
        tool_list = None

    if tool_list:
        for tool in tool_list.values():
            try:
                tool.SetInput("StyledText", text)
                return True
            except Exception:
                continue
    return False


def _set_title_duration(title_item, duration_frames: int) -> bool:
    if duration_frames <= 0:
        return False
    try:
        return bool(title_item.SetProperty("Duration", duration_frames))
    except Exception:
        return False


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

    print("Note: Crossfades between images are not currently supported by the Resolve scripting API.")

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

    timestamps_path = artifacts.get("timestamps_path")
    textplus_name = project_info.get("textplus_preset") or "Text+"
    textplus_failed = False
    if timestamps_path and Path(timestamps_path).exists():
        try:
            with open(timestamps_path, "r", encoding="utf-8") as handle:
                timestamps_data = json.load(handle)
            captions = timestamps_data.get("captions", [])
        except Exception:
            captions = []

        if captions:
            print(f"Adding {len(captions)} Text+ captions using preset '{textplus_name}'...")
            for caption in captions:
                start = float(caption.get("start", 0))
                end = float(caption.get("end", start))
                duration_frames = max(1, int(round((end - start) * frame_rate)))
                timecode = _seconds_to_timecode(start, frame_rate)
                if hasattr(project, "SetCurrentTimecode"):
                    project.SetCurrentTimecode(timecode)

                title_item = timeline.InsertFusionTitleIntoTimeline(textplus_name)
                if not title_item:
                    print(f"Failed to insert Text+ at {timecode}")
                    textplus_failed = True
                    break

                if not _set_title_duration(title_item, duration_frames):
                    print("Warning: could not set title duration; using default.")

                if not _set_title_text(title_item, caption.get("text", "")):
                    print("Warning: could not set Text+ content for a caption.")
                print("Note: Text+ fade in/out is not currently supported by the scripting API.")

    if textplus_failed:
        srt_path = artifacts.get("srt_path")
        if srt_path and Path(srt_path).exists():
            items = media_pool.ImportMedia([srt_path])
            if items:
                print("Text+ preset failed. Imported SRT into Media Pool.")
                print("Manual step: Right-click the subtitle clip and choose")
                print("'Insert Selected Subtitles to Timeline Using Timecode'.")
            else:
                print("Text+ preset failed and SRT import did not succeed.")

    print("NarrationDeck import complete.")


if __name__ == "__main__":
    main()
