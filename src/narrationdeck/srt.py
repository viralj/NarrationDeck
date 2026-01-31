from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WordTiming:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class Caption:
    start: float
    end: float
    text: str


def alignment_to_words(alignment: dict) -> list[WordTiming]:
    characters = alignment.get("characters", [])
    starts = alignment.get("character_start_times_seconds", [])
    ends = alignment.get("character_end_times_seconds", [])
    if not (len(characters) == len(starts) == len(ends)):
        raise ValueError("Alignment arrays are mismatched.")

    words: list[WordTiming] = []
    current = []
    current_start = None
    current_end = None

    for ch, start, end in zip(characters, starts, ends):
        if ch.isspace():
            if current:
                words.append(WordTiming("".join(current), current_start or 0.0, current_end or 0.0))
                current = []
                current_start = None
                current_end = None
            continue

        if current_start is None:
            current_start = float(start)
        current.append(ch)
        current_end = float(end)

    if current:
        words.append(WordTiming("".join(current), current_start or 0.0, current_end or 0.0))

    return words


def words_to_captions(
    words: list[WordTiming],
    *,
    max_caption_chars: int = 80,
    max_caption_duration: float = 4.0,
    min_sentence_duration: float = 1.2,
) -> list[Caption]:
    captions: list[Caption] = []
    current_words: list[WordTiming] = []
    current_len = 0
    start_time = 0.0

    for word in words:
        if not current_words:
            start_time = word.start
            current_len = 0

        proposed_len = current_len + (1 if current_words else 0) + len(word.text)
        duration = word.end - start_time
        sentence_end = word.text.endswith((".", "!", "?", "…"))

        if current_words and (proposed_len > max_caption_chars or duration > max_caption_duration):
            captions.append(_finalize_caption(current_words, start_time))
            current_words = [word]
            current_len = len(word.text)
            start_time = word.start
            continue

        current_words.append(word)
        current_len = proposed_len

        if sentence_end and duration >= min_sentence_duration:
            captions.append(_finalize_caption(current_words, start_time))
            current_words = []
            current_len = 0

    if current_words:
        captions.append(_finalize_caption(current_words, start_time))

    return captions


def captions_to_srt(captions: list[Caption]) -> str:
    lines = []
    for idx, caption in enumerate(captions, start=1):
        lines.append(str(idx))
        lines.append(f"{_format_time(caption.start)} --> {_format_time(caption.end)}")
        lines.append(caption.text)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _finalize_caption(words: list[WordTiming], start_time: float) -> Caption:
    end_time = words[-1].end
    text = _wrap_lines(" ".join(word.text for word in words))
    return Caption(start=start_time, end=end_time, text=text)


def _wrap_lines(text: str, max_line_chars: int = 42) -> str:
    words = text.split()
    if not words:
        return ""
    lines: list[str] = []
    current = []
    current_len = 0
    for word in words:
        proposed_len = current_len + (1 if current else 0) + len(word)
        if current and proposed_len > max_line_chars:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len = proposed_len
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines[:2])


def _format_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
