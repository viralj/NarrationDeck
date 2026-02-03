from __future__ import annotations

import re
from dataclasses import dataclass

from .srt import WordTiming


@dataclass(frozen=True)
class ImageAnchor:
    image_id: str
    snippet: str


@dataclass(frozen=True)
class ImageSegment:
    image_id: str
    start: float
    end: float
    snippet: str
    match_index: int


_ANCHOR_PATTERN = re.compile(r"^\s*image\s*(\d+)\s*:\s*(.+)$", re.IGNORECASE)


def parse_image_anchors(text: str) -> list[ImageAnchor]:
    anchors: list[ImageAnchor] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = _ANCHOR_PATTERN.match(line)
        if not match:
            continue
        image_num = match.group(1)
        snippet = match.group(2).strip()
        if snippet:
            anchors.append(ImageAnchor(image_id=image_num.zfill(2), snippet=snippet))
    return anchors


def build_image_segments(
    *,
    anchors: list[ImageAnchor],
    words: list[WordTiming],
    allow_missing: bool = False,
) -> list[ImageSegment]:
    if not anchors:
        return []

    normalized_words = [_normalize_token(word.text) for word in words]
    segments: list[ImageSegment] = []
    missing: list[str] = []

    start_times: list[tuple[ImageAnchor, int, float]] = []
    for anchor in anchors:
        snippet_tokens = _normalize_text(anchor.snippet).split()
        if not snippet_tokens:
            missing.append(anchor.image_id)
            continue
        match_index = _find_subsequence(normalized_words, snippet_tokens)
        if match_index is None:
            missing.append(anchor.image_id)
            continue
        start_time = words[match_index].start
        start_times.append((anchor, match_index, start_time))

    if missing and not allow_missing:
        missing_ids = ", ".join(missing)
        raise ValueError(f"Could not match snippet for images: {missing_ids}")

    for idx, (anchor, match_index, start_time) in enumerate(start_times):
        if idx + 1 < len(start_times):
            end_time = start_times[idx + 1][2]
        else:
            end_time = words[-1].end if words else start_time
        if end_time < start_time:
            raise ValueError(f"Invalid timing for image {anchor.image_id} (end before start).")
        segments.append(
            ImageSegment(
                image_id=anchor.image_id,
                start=start_time,
                end=end_time,
                snippet=anchor.snippet,
                match_index=match_index,
            )
        )

    return segments


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("…", " ")
    text = re.sub(r"[\"'“”‘’]", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    if not text:
        return text
    return _normalize_number_words(text)


def _normalize_token(token: str) -> str:
    return _normalize_text(token)


_UNITS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
}
_TENS = {
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def _normalize_number_words(text: str) -> str:
    tokens = text.split()
    out: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in _UNITS and i + 2 < len(tokens) and tokens[i + 1] == "point" and tokens[i + 2] in _UNITS:
            out.append(str(_UNITS[token]))
            out.append(str(_UNITS[tokens[i + 2]]))
            i += 3
            continue

        if token in _TENS:
            value = _TENS[token]
            if i + 1 < len(tokens) and tokens[i + 1] in _UNITS:
                value += _UNITS[tokens[i + 1]]
                i += 2
            else:
                i += 1
            out.append(str(value))
            continue

        if token in _UNITS:
            out.append(str(_UNITS[token]))
            i += 1
            continue

        out.append(token)
        i += 1

    return " ".join(out)


def _find_subsequence(words: list[str], snippet: list[str]) -> int | None:
    if not snippet:
        return None
    last_start = len(words) - len(snippet)
    for start in range(0, last_start + 1):
        if words[start : start + len(snippet)] == snippet:
            return start
    return None
