from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed" / "passages.json"
MANIFEST = ROOT / "data" / "seed" / "source_manifest.json"
DOWNLOADS = ROOT / "data" / "raw" / "downloads"
OUT = ROOT / "data" / "processed" / "passages.json"

import sys

sys.path.insert(0, str(ROOT))
from roadlegal.text import split_chunks, strip_html  # noqa: E402


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return read_pdf(path)
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if suffix in {".html", ".htm"}:
        return strip_html(raw)
    return raw


def select_content(text: str, source: dict) -> str:
    """Trim known page chrome while preserving the official article text."""
    selected = text
    start_marker = source.get("content_start")
    if start_marker:
        if source.get("content_start_mode") == "last":
            start = selected.rfind(start_marker)
        else:
            start = selected.find(start_marker)
        if start >= 0:
            selected = selected[start:]

    end_marker = source.get("content_end")
    if end_marker:
        end = selected.find(end_marker)
        if end >= 0:
            selected = selected[:end]
    return selected.strip()


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    passages = json.loads(SEED.read_text(encoding="utf-8"))
    seen = {hashlib.sha1(" ".join(item["text"].casefold().split()).encode("utf-8")).hexdigest() for item in passages}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    added_by_source: Counter[str] = Counter()
    for source in manifest["sources"]:
        path = DOWNLOADS / source["filename"]
        if not path.exists() or path.stat().st_size == 0:
            continue
        try:
            text = select_content(read_document(path), source)
        except Exception as exc:
            print(f"skip {source['id']}: {type(exc).__name__}: {exc}")
            continue
        for index, chunk in enumerate(split_chunks(text)):
            normalized = " ".join(chunk.casefold().split())
            content_hash = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
            if len(normalized) < 120 or content_hash in seen:
                continue
            seen.add(content_hash)
            digest = hashlib.sha1(f"{source['id']}:{index}:{chunk[:80]}".encode("utf-8")).hexdigest()[:12]
            passages.append(
                {
                    "id": f"download:{source['id']}:{digest}",
                    "title": f"{source['title']} chunk {index + 1}",
                    "text": chunk,
                    "jurisdiction": source["jurisdiction"],
                    "country": source["country"],
                    "source_title": source["title"],
                    "source_url": source["url"],
                    "tags": source.get("tags", []),
                    "verified": bool(source.get("verified", False)),
                    "source_type": source.get("source_type", "reference"),
                    "review_status": source.get("review_status", "needs_review"),
                    "published_date": source.get("published_date"),
                    "effective_date": source.get("effective_date"),
                    "language": source.get("language", "English"),
                }
            )
            added_by_source[source["id"]] += 1
    OUT.write_text(json.dumps(passages, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(passages)} passages to {OUT}")
    for source_id, count in added_by_source.most_common():
        print(f"  {source_id}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
