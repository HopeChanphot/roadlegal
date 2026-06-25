from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "seed" / "source_manifest.json"
OUT_DIR = ROOT / "data" / "raw" / "downloads"


def download(url: str, target: Path) -> tuple[bool, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "RoadLegal-Hackathon-RAG/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            target.write_bytes(response.read())
        return True, "downloaded"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return False, str(exc.reason)
    except TimeoutError:
        return False, "timeout"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures = []
    for source in manifest["sources"]:
        filename = source["filename"]
        url = source["url"]
        target = OUT_DIR / filename
        if target.exists() and target.stat().st_size > 0:
            print(f"skip {filename}")
            continue
        ok, message = download(url, target)
        status = "ok" if ok else "failed"
        print(f"{status} {filename}: {message}")
        if not ok:
            failures.append((filename, message))
    if failures:
        print("\nSome sources could not be downloaded. The seed passages still allow the app to run.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
