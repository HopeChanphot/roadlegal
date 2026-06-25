from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .challan import ChallanCalculator
from .geo import jurisdiction_from_text
from .llm_runtime import LocalLLMRuntime
from .paths import PROCESSED_DIR, SEED_DIR
from .text import normalize_space, tokenize


INDEX_FILE = PROCESSED_DIR / "passages.json"
SEED_PASSAGES = SEED_DIR / "passages.json"


@dataclass
class Passage:
    id: str
    title: str
    text: str
    jurisdiction: str
    country: str
    source_title: str
    source_url: str
    tags: list[str]
    verified: bool = False


class RoadLegalRAG:
    def __init__(self, index_file: Path = INDEX_FILE) -> None:
        self.index_file = index_file if index_file.exists() else SEED_PASSAGES
        self.passages = self._load_passages(self.index_file)
        self.doc_terms: list[Counter[str]] = []
        self.doc_lengths: list[int] = []
        self.idf: dict[str, float] = {}
        self._build_index()
        self.calculator = ChallanCalculator()
        self.llm = LocalLLMRuntime()

    def health(self) -> dict[str, Any]:
        status = self.llm.status()
        jurisdictions = sorted({p.jurisdiction for p in self.passages})
        return {
            "passages": len(self.passages),
            "index_file": str(self.index_file),
            "jurisdictions": jurisdictions,
            "model": asdict(status),
        }

    def search(self, query: str, jurisdiction: str = "india_national", k: int = 6) -> list[dict[str, Any]]:
        terms = tokenize(query)
        if not terms:
            return []
        scores: list[tuple[float, Passage]] = []
        avg_len = sum(self.doc_lengths) / max(1, len(self.doc_lengths))
        for idx, passage in enumerate(self.passages):
            score = self._bm25_score(terms, self.doc_terms[idx], self.doc_lengths[idx], avg_len)
            if passage.jurisdiction == jurisdiction:
                score *= 1.28
            elif passage.jurisdiction in {"global", "bimstec"}:
                score *= 1.08
            elif jurisdiction.split("_", 1)[0] in passage.jurisdiction:
                score *= 1.1
            if any(term in passage.tags for term in terms):
                score += 0.8
            if score > 0:
                scores.append((score, passage))
        scores.sort(key=lambda item: item[0], reverse=True)
        return [{"score": round(score, 3), **asdict(passage)} for score, passage in scores[:k]]

    def answer(self, message: str, jurisdiction: str = "india_national", language: str = "English") -> dict[str, Any]:
        inferred = jurisdiction_from_text(message, jurisdiction)
        jurisdiction = inferred or jurisdiction
        retrieved = self.search(message, jurisdiction=jurisdiction, k=5)
        fine = self._maybe_calculate(message, jurisdiction)
        prompt = self._prompt(message, jurisdiction, language, retrieved, fine)
        generated = self.llm.generate(prompt)
        if generated:
            answer_text = generated
            mode = "generative-rag"
        else:
            answer_text = self._extractive_answer(message, jurisdiction, retrieved, fine)
            mode = "extractive-rag"
        return {
            "answer": answer_text,
            "mode": mode,
            "jurisdiction": jurisdiction,
            "language": language,
            "citations": [
                {
                    "title": item["source_title"],
                    "url": item["source_url"],
                    "passage": item["title"],
                    "country": item["country"],
                    "verified": item["verified"],
                }
                for item in retrieved
            ],
            "fine": fine,
            "model": asdict(self.llm.status()),
        }

    def _maybe_calculate(self, message: str, jurisdiction: str) -> dict[str, Any] | None:
        lowered = message.lower()
        fine_terms = ["fine", "challan", "penalty", "how much", "ticket"]
        offence_terms = ["speed", "helmet", "seat", "drunk", "drink", "license", "licence", "phone", "insurance", "registration"]
        if not any(term in lowered for term in fine_terms + offence_terms):
            return None
        vehicle = "light_motor_vehicle"
        if "motorcycle" in lowered or "bike" in lowered or "two wheeler" in lowered or "scooter" in lowered:
            vehicle = "two_wheeler"
        if "truck" in lowered or "heavy" in lowered or "bus" in lowered:
            vehicle = "heavy_vehicle"
        result = self.calculator.calculate(jurisdiction, lowered, vehicle)
        return asdict(result)

    def _extractive_answer(
        self,
        message: str,
        jurisdiction: str,
        retrieved: list[dict[str, Any]],
        fine: dict[str, Any] | None,
    ) -> str:
        lines = []
        if fine:
            lines.append(f"Challan estimate for {fine['jurisdiction'].replace('_', ' ')}: {fine['amount_display']}.")
            if fine.get("legal_basis"):
                lines.append(f"Legal basis: {fine['legal_basis']}.")
            if fine.get("consequences"):
                lines.append("Possible consequences: " + "; ".join(fine["consequences"]) + ".")
            if fine.get("caveats"):
                lines.append("Caveat: " + " ".join(fine["caveats"]))

        if retrieved:
            lines.append("Grounded answer:")
            for item in retrieved[:3]:
                snippet = normalize_space(item["text"])
                if len(snippet) > 260:
                    snippet = snippet[:257].rsplit(" ", 1)[0] + "..."
                lines.append(f"- {snippet} [{item['source_title']}]")
        else:
            lines.append("I do not have enough local source material to answer that safely yet.")

        tip = self._safety_tip(message)
        if tip:
            lines.append(f"Safety coach: {tip}")
        lines.append("This is an informational estimate, not legal advice. Verify urgent or disputed matters with the local traffic authority.")
        return "\n".join(lines)

    def _safety_tip(self, message: str) -> str | None:
        lowered = message.lower()
        if "helmet" in lowered or "bike" in lowered or "motorcycle" in lowered:
            return "Correct helmet use sharply reduces death and brain-injury risk; replace damaged helmets and fasten the strap."
        if "speed" in lowered:
            return "Small speed increases raise both crash likelihood and injury severity, so match speed to road, weather, and pedestrian activity."
        if "seat" in lowered or "belt" in lowered:
            return "Seat belts reduce fatal injury risk for vehicle occupants and should be used on every trip, including short city trips."
        if "drink" in lowered or "alcohol" in lowered or "drunk" in lowered:
            return "Alcohol impairment begins before a driver feels obviously drunk; use a sober driver or public transport."
        return None

    def _prompt(
        self,
        message: str,
        jurisdiction: str,
        language: str,
        retrieved: list[dict[str, Any]],
        fine: dict[str, Any] | None,
    ) -> str:
        context = "\n\n".join(
            f"Source: {item['source_title']} ({item['source_url']})\nText: {item['text']}" for item in retrieved[:5]
        )
        fine_text = json.dumps(fine, ensure_ascii=True) if fine else "No structured fine estimate."
        return (
            "You are RoadLegal, an offline road-safety legal information assistant for BIMSTEC countries. "
            "Use only the context below. Give cautious, concise answers with citations. "
            "If the context is insufficient, say so.\n\n"
            f"Jurisdiction: {jurisdiction}\nLanguage: {language}\nFine estimate: {fine_text}\n\n"
            f"Context:\n{context}\n\nUser question: {message}\nAnswer:"
        )

    def _load_passages(self, path: Path) -> list[Passage]:
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return [Passage(**item) for item in raw]

    def _build_index(self) -> None:
        document_frequency: dict[str, int] = defaultdict(int)
        for passage in self.passages:
            terms = Counter(tokenize(" ".join([passage.title, passage.text, " ".join(passage.tags)])))
            self.doc_terms.append(terms)
            self.doc_lengths.append(sum(terms.values()))
            for term in terms:
                document_frequency[term] += 1
        count = max(1, len(self.passages))
        self.idf = {
            term: math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def _bm25_score(self, query_terms: list[str], terms: Counter[str], doc_len: int, avg_len: float) -> float:
        k1 = 1.5
        b = 0.75
        score = 0.0
        for term in query_terms:
            frequency = terms.get(term, 0)
            if not frequency:
                continue
            numerator = frequency * (k1 + 1)
            denominator = frequency + k1 * (1 - b + b * doc_len / max(1.0, avg_len))
            score += self.idf.get(term, 0.0) * numerator / denominator
        return score
