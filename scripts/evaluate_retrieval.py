from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from roadlegal.rag import RoadLegalRAG  # noqa: E402


CASES = [
    ("What is the overspeeding fine in India?", "india_national", "India Motor Vehicles Act"),
    ("What is the motorcycle helmet fine in Thailand?", "thailand_national", "Thailand PRD traffic penalties"),
    ("ไม่สวมหมวกกันน็อก ปรับเท่าไหร่", "thailand_national", "Thailand PRD traffic penalties"),
    ("How do vehicle registration and driving licences work in Bhutan?", "bhutan_national", "Bhutan Road Safety"),
    ("What do official sources say about speed and helmets in Nepal?", "nepal_national", "WHO Road safety Nepal"),
    ("What is known about motorcycle helmet law in Myanmar?", "myanmar_national", "WHO Road safety Myanmar"),
    ("What is the Motor Traffic Act penalty framework in Sri Lanka?", "sri_lanka_national", "Sri Lanka Motor Traffic Act"),
]


def main() -> int:
    rag = RoadLegalRAG()
    passed = 0
    reciprocal_ranks = []
    rows = []
    for query, jurisdiction, expected_source in CASES:
        results, diagnostics = rag.search_with_diagnostics(query, jurisdiction=jurisdiction, k=5)
        rank = next(
            (index for index, item in enumerate(results, start=1) if expected_source.casefold() in item["source_title"].casefold()),
            None,
        )
        allowed = {jurisdiction, "global", "bimstec"}
        if jurisdiction == "delhi":
            allowed.add("india_national")
        isolated = all(item["jurisdiction"] in allowed for item in results)
        ok = rank is not None and isolated
        passed += int(ok)
        reciprocal_ranks.append(1 / rank if rank else 0)
        rows.append(
            {
                "ok": ok,
                "query": query,
                "jurisdiction": jurisdiction,
                "expected_source": expected_source,
                "rank": rank,
                "isolated": isolated,
                "latency_ms": diagnostics["latency_ms"],
                "top_sources": [item["source_title"] for item in results[:3]],
            }
        )
    report = {
        "passed": passed,
        "total": len(CASES),
        "mean_reciprocal_rank": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 3),
        "cases": rows,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
