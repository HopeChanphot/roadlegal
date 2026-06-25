from __future__ import annotations

import hashlib
import json
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


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    passages = json.loads(SEED.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for source in manifest["sources"]:
        path = DOWNLOADS / source["filename"]
        if not path.exists() or path.stat().st_size == 0:
            continue
        text = read_document(path)
        for index, chunk in enumerate(split_chunks(text)):
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
                    "verified": True,
                }
            )
    OUT.write_text(json.dumps(passages, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(passages)} passages to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
