from __future__ import annotations

import base64
import json
from urllib import request


BASE_URL = "https://api.elevenlabs.io/v1"


class ElevenLabsError(RuntimeError):
    pass


def synthesize_with_timestamps(
    *,
    text: str,
    voice_id: str,
    model_id: str,
    api_key: str,
    speed: float,
) -> dict:
    url = f"{BASE_URL}/text-to-speech/{voice_id}/with-timestamps"

    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "speed": speed,
        },
    }

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as resp:
            data = resp.read().decode("utf-8")
    except Exception as exc:
        raise ElevenLabsError(f"Request failed: {exc}") from exc

    try:
        result = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ElevenLabsError("Invalid JSON response from ElevenLabs.") from exc

    if "audio_base64" not in result or "alignment" not in result:
        raise ElevenLabsError("Missing audio or alignment in ElevenLabs response.")

    try:
        audio_bytes = base64.b64decode(result["audio_base64"])
    except Exception as exc:
        raise ElevenLabsError("Failed to decode audio data.") from exc

    return {
        "audio_bytes": audio_bytes,
        "alignment": result["alignment"],
        "raw": result,
    }
