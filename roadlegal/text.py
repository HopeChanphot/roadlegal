import re
from html import unescape


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def normalize_space(value: str) -> str:
    return SPACE_RE.sub(" ", value or "").strip()


def tokenize(value: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(value or "")]


def strip_html(value: str) -> str:
    text = TAG_RE.sub(" ", value or "")
    return normalize_space(unescape(text))


def split_chunks(text: str, max_chars: int = 1200, overlap: int = 140) -> list[str]:
    clean = normalize_space(text)
    if len(clean) <= max_chars:
        return [clean] if clean else []

    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + max_chars, len(clean))
        cut = clean.rfind(". ", start, end)
        if cut > start + int(max_chars * 0.55):
            end = cut + 1
        chunk = normalize_space(clean[start:end])
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        start = max(0, end - overlap)
    return chunks
