from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT))
from roadlegal.challan import ChallanCalculator  # noqa: E402
from roadlegal.game_content import quiz_for  # noqa: E402
from roadlegal.rag import INDEX_FILE, SEED_PASSAGES  # noqa: E402


OUT = ROOT / "web" / "static-data.json"
FINE_FILE = ROOT / "data" / "seed" / "fine_schedule.json"


def main() -> int:
    calculator = ChallanCalculator()
    index_file = INDEX_FILE if INDEX_FILE.exists() else SEED_PASSAGES
    passages = json.loads(index_file.read_text(encoding="utf-8"))
    fine_schedule = json.loads(FINE_FILE.read_text(encoding="utf-8"))
    jurisdictions = calculator.jurisdictions()
    quizzes = {item["id"]: quiz_for(item["id"]) for item in jurisdictions}
    payload = {
        "health": {
            "passages": len(passages),
            "index_file": "static-data.json",
            "jurisdictions": sorted({item["jurisdiction"] for item in passages}),
            "model": {
                "mode": "static-rag",
                "llama_cli": None,
                "llama_server": None,
                "gguf_model": None,
                "cached_hf_model": None,
                "note": "GitHub Pages static demo. Answers are generated in-browser from packaged RAG data.",
            },
        },
        "jurisdictions": jurisdictions,
        "fine_schedule": fine_schedule,
        "passages": passages,
        "quizzes": quizzes,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote static demo data with {len(passages)} passages to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
