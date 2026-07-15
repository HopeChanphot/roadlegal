from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "models" / "Qwen3-0.6B-Q8_0.gguf"
URL = "https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q8_0.gguf"
EXPECTED_SIZE = 639_446_688
EXPECTED_SHA256 = "9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.exists() and TARGET.stat().st_size == EXPECTED_SIZE and sha256(TARGET) == EXPECTED_SHA256:
        print(f"model already verified: {TARGET}")
        return 0
    temporary = TARGET.with_suffix(".gguf.tmp")
    request = urllib.request.Request(URL, headers={"User-Agent": "RoadLegal-Hackathon/0.2"})
    downloaded = 0
    next_report = 64 * 1024 * 1024
    with urllib.request.urlopen(request, timeout=90) as response, temporary.open("wb") as output:
        while True:
            block = response.read(4 * 1024 * 1024)
            if not block:
                break
            output.write(block)
            downloaded += len(block)
            if downloaded >= next_report:
                print(f"downloaded {downloaded / (1024 * 1024):.0f} MiB / {EXPECTED_SIZE / (1024 * 1024):.0f} MiB")
                next_report += 64 * 1024 * 1024
    if downloaded != EXPECTED_SIZE:
        print(f"size verification failed: expected {EXPECTED_SIZE}, received {downloaded}")
        return 1
    actual_hash = sha256(temporary)
    if actual_hash != EXPECTED_SHA256:
        print(f"SHA-256 verification failed: {actual_hash}")
        return 1
    temporary.replace(TARGET)
    print(f"model verified: {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
