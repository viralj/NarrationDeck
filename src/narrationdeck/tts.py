from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .elevenlabs import synthesize_with_timestamps
from .srt import alignment_to_words, words_to_captions, captions_to_srt


def generate_audio_and_srt(
    *,
    output_dir: str,
    text: str,
    voice: dict,
    speed: float,
    output_format: str,
    api_key: str,
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

    audio_filename = f"narration_{run_id}.mp3"
    srt_filename = f"narration_{run_id}.srt"
    timestamps_filename = f"narration_{run_id}_timestamps.json"

    audio_path = output_path / audio_filename
    srt_path = output_path / srt_filename
    timestamps_path = output_path / timestamps_filename

    audio_path.write_bytes(result["audio_bytes"])

    words = alignment_to_words(result["alignment"])
    captions = words_to_captions(words)
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

    return {
        "audio_path": str(audio_path),
        "srt_path": str(srt_path),
        "timestamps_path": str(timestamps_path),
        "note": " ".join(notes).strip() if notes else None,
    }
