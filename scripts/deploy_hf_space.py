from __future__ import annotations

import os
import sys
from pathlib import Path

from huggingface_hub import HfApi


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPACE = "chanphot/roadlegal"
SPACE_DIR = ROOT / "hf_space"


def main() -> int:
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN is required. Create a Hugging Face write token and add it as a GitHub Actions secret.")
        return 2
    repo_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("HF_SPACE_ID", DEFAULT_SPACE)
    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="gradio", exist_ok=True)
    api.upload_folder(
        repo_id=repo_id,
        repo_type="space",
        folder_path=SPACE_DIR,
        commit_message="Deploy RoadLegal AI backend",
        ignore_patterns=["__pycache__/**", "*.pyc"],
    )
    print(f"Space deployment uploaded: https://huggingface.co/spaces/{repo_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
