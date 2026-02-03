from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .elevenlabs import synthesize_with_timestamps
from .srt import alignment_to_words, words_to_captions, captions_to_srt
from .mapping import parse_image_anchors, build_image_segments, debug_missing_anchors
from .srt import WordTiming


def generate_audio_and_srt(
    *,
    output_dir: str,
    text: str,
    voice: dict,
    speed: float,
    output_format: str,
    api_key: str,
    output_prefix: str = "narration",
    image_map_text: str | None = None,
    allow_missing_image_anchors: bool = False,
    caption_max_chars: int | None = 80,
    caption_max_duration: float | None = 4.0,
    caption_line_chars: int | None = 42,
) -> dict:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    voice_id = voice.get("voice_id")
    model_id = voice.get("model_id")
    if not voice_id or not model_id:
        raise ValueError("Selected voice is missing voice_id or model_id.")

    notes: list[str] = []
    if output_format.lower() != "mp3":
        notes.append("WAV output is not supported yet; generated MP3 instead.")
        output_format = "mp3"

    if speed < 0.7:
        speed = 0.7
        notes.append("Speed clamped to 0.7.")
    elif speed > 1.2:
        speed = 1.2
        notes.append("Speed clamped to 1.2.")

    result = synthesize_with_timestamps(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        api_key=api_key,
        speed=speed,
    )

    safe_prefix = _safe_prefix(output_prefix) or "narration"
    audio_filename = f"{safe_prefix}_{run_id}.mp3"
    srt_filename = f"{safe_prefix}_{run_id}.srt"
    timestamps_filename = f"{safe_prefix}_{run_id}_timestamps.json"
    image_timeline_filename = f"{safe_prefix}_{run_id}_image_timeline.json"
    image_report_filename = f"{safe_prefix}_{run_id}_image_report.txt"

    audio_path = output_path / audio_filename
    srt_path = output_path / srt_filename
    timestamps_path = output_path / timestamps_filename
    image_timeline_path = output_path / image_timeline_filename
    image_report_path = output_path / image_report_filename

    audio_path.write_bytes(result["audio_bytes"])

    words = alignment_to_words(result["alignment"])
    use_limits = (
        caption_max_chars is not None
        and caption_max_duration is not None
        and caption_line_chars is not None
    )
    captions = words_to_captions(
        words,
        max_caption_chars=caption_max_chars if use_limits else None,
        max_caption_duration=caption_max_duration if use_limits else None,
        max_line_chars=caption_line_chars if caption_line_chars is not None else 42,
        max_lines=2 if use_limits else None,
    )
    srt_text = captions_to_srt(captions)
    srt_path.write_text(srt_text, encoding="utf-8")

    timestamps_payload = {
        "voice": voice,
        "speed": speed,
        "alignment": result["alignment"],
        "words": [word.__dict__ for word in words],
        "captions": [caption.__dict__ for caption in captions],
    }
    timestamps_path.write_text(json.dumps(timestamps_payload, indent=2), encoding="utf-8")

    image_segments = []
    missing_images: list[str] = []
    if image_map_text:
        anchors = parse_image_anchors(image_map_text)
        if anchors:
            image_segments = build_image_segments(
                anchors=anchors, words=words, allow_missing=allow_missing_image_anchors
            )
            matched_ids = {segment.image_id for segment in image_segments}
            missing_images = [anchor.image_id for anchor in anchors if anchor.image_id not in matched_ids]
            image_payload = {
                "anchors": [anchor.__dict__ for anchor in anchors],
                "segments": [segment.__dict__ for segment in image_segments],
                "missing": missing_images,
            }
            image_timeline_path.write_text(json.dumps(image_payload, indent=2), encoding="utf-8")
            image_report_path.write_text(
                _format_image_report(image_segments, missing_images),
                encoding="utf-8",
            )

    return {
        "audio_path": str(audio_path),
        "srt_path": str(srt_path),
        "timestamps_path": str(timestamps_path),
        "image_timeline_path": str(image_timeline_path) if image_segments else None,
        "image_report_path": str(image_report_path) if image_segments else None,
        "image_segments": [segment.__dict__ for segment in image_segments],
        "missing_images": missing_images,
        "note": " ".join(notes).strip() if notes else None,
    }


def build_image_timeline_from_timestamps(
    *,
    output_dir: str,
    timestamps_path: str,
    image_map_text: str,
    allow_missing_image_anchors: bool,
    output_prefix: str,
) -> dict:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    safe_prefix = _safe_prefix(output_prefix) or "narration"
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    image_timeline_filename = f"{safe_prefix}_{run_id}_image_timeline.json"
    image_report_filename = f"{safe_prefix}_{run_id}_image_report.txt"
    image_timeline_path = output_path / image_timeline_filename
    image_report_path = output_path / image_report_filename

    data = json.loads(Path(timestamps_path).read_text(encoding="utf-8"))
    words_data = data.get("words", [])
    if words_data:
        words = [WordTiming(**item) for item in words_data]
    else:
        alignment = data.get("alignment")
        if not alignment:
            raise ValueError("Timestamps JSON missing words or alignment.")
        words = alignment_to_words(alignment)

    anchors = parse_image_anchors(image_map_text)
    if not anchors:
        raise ValueError("No image anchors provided.")

    try:
        image_segments = build_image_segments(
            anchors=anchors,
            words=words,
            allow_missing=allow_missing_image_anchors,
        )
    except ValueError as exc:
        debug_path = output_path / f"{safe_prefix}_{run_id}_anchor_debug.txt"
        debug_path.write_text(debug_missing_anchors(anchors, words), encoding="utf-8")
        raise ValueError(f"{exc}. Debug report written to {debug_path}") from exc
    matched_ids = {segment.image_id for segment in image_segments}
    missing_images = [anchor.image_id for anchor in anchors if anchor.image_id not in matched_ids]

    image_payload = {
        "anchors": [anchor.__dict__ for anchor in anchors],
        "segments": [segment.__dict__ for segment in image_segments],
        "missing": missing_images,
    }
    image_timeline_path.write_text(json.dumps(image_payload, indent=2), encoding="utf-8")
    image_report_path.write_text(
        _format_image_report(image_segments, missing_images),
        encoding="utf-8",
    )

    return {
        "image_timeline_path": str(image_timeline_path),
        "image_report_path": str(image_report_path),
        "image_segments": [segment.__dict__ for segment in image_segments],
        "missing_images": missing_images,
    }


def _safe_prefix(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum() or ch in ("-", "_")).strip()


def _format_image_report(image_segments: list, missing_images: list[str]) -> str:
    lines = ["Image Anchor Report", "====================", ""]
    for segment in image_segments:
        lines.append(
            f"Image {segment.image_id} | {segment.start:.3f}s -> {segment.end:.3f}s"
        )
        lines.append(f"  Snippet: {segment.snippet}")
        lines.append(f"  Match word index: {segment.match_index}")
        lines.append("")
    if missing_images:
        lines.append("Missing anchors:")
        for image_id in missing_images:
            lines.append(f"  Image {image_id}")
    return "\n".join(lines).rstrip() + "\n"
