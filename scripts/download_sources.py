from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "seed" / "source_manifest.json"
OUT_DIR = ROOT / "data" / "raw" / "downloads"
REPORT = ROOT / "data" / "processed" / "source_download_report.json"


def download(url: str, target: Path) -> tuple[bool, str, dict[str, object]]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 RoadLegal-Hackathon-RAG/0.2",
            "Accept": "application/pdf,text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
    )
    last_message = "unknown error"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read()
                content_type = response.headers.get_content_type()
                final_url = response.geturl()
            if len(body) < 500:
                return False, "response was too small", {"bytes": len(body), "content_type": content_type, "final_url": final_url}
            if target.suffix.lower() == ".pdf" and not body.lstrip().startswith(b"%PDF"):
                return False, "expected PDF but received another format", {
                    "bytes": len(body),
                    "content_type": content_type,
                    "final_url": final_url,
                }
            temporary = target.with_suffix(target.suffix + ".tmp")
            temporary.write_bytes(body)
            temporary.replace(target)
            return True, "downloaded", {"bytes": len(body), "content_type": content_type, "final_url": final_url}
        except urllib.error.HTTPError as exc:
            last_message = f"HTTP {exc.code}"
        except urllib.error.URLError as exc:
            last_message = str(exc.reason)
        except TimeoutError:
            last_message = "timeout"
        if attempt < 2:
            time.sleep(1.5 * (attempt + 1))
    return False, last_message, {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Download RoadLegal authoritative RAG sources")
    parser.add_argument("--force", action="store_true", help="replace existing downloads")
    parser.add_argument("--source", action="append", default=[], help="only download a source id; repeat as needed")
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures = []
    report = []
    for source in manifest["sources"]:
        if args.source and source["id"] not in args.source:
            continue
        filename = source["filename"]
        url = source.get("download_url", source["url"])
        target = OUT_DIR / filename
        if target.exists() and target.stat().st_size > 0 and not args.force:
            print(f"skip {filename}")
            report.append({"id": source["id"], "status": "cached", "bytes": target.stat().st_size, "url": url})
            continue
        ok, message, details = download(url, target)
        status = "ok" if ok else "failed"
        print(f"{status} {filename}: {message}")
        report.append({"id": source["id"], "status": status, "message": message, "url": url, **details})
        if not ok:
            failures.append((filename, message))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if REPORT.exists():
        try:
            existing = {item["id"]: item for item in json.loads(REPORT.read_text(encoding="utf-8")).get("sources", [])}
        except (json.JSONDecodeError, KeyError):
            existing = {}
    existing.update({item["id"]: item for item in report})
    ordered_report = [existing[source["id"]] for source in manifest["sources"] if source["id"] in existing]
    REPORT.write_text(json.dumps({"sources": ordered_report}, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        print("\nSome sources could not be downloaded. The seed passages still allow the app to run.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
