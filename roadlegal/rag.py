from __future__ import annotations

import json
import math
import re
import threading
import time
from collections import OrderedDict
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .challan import ChallanCalculator
from .geo import jurisdiction_from_text
from .llm_runtime import LocalLLMRuntime
from .paths import PROCESSED_DIR, SEED_DIR
from .text import QUERY_ALIASES, expand_query, normalize_space, tokenize


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
    source_type: str = "reference"
    review_status: str = "needs_review"
    published_date: str | None = None
    effective_date: str | None = None
    language: str = "English"


class RoadLegalRAG:
    def __init__(self, index_file: Path = INDEX_FILE) -> None:
        self.index_file = index_file if index_file.exists() else SEED_PASSAGES
        self.passages = self._load_passages(self.index_file)
        self.body_terms: list[Counter[str]] = []
        self.title_terms: list[Counter[str]] = []
        self.tag_terms: list[Counter[str]] = []
        self.doc_terms: list[Counter[str]] = []
        self.doc_lengths: list[int] = []
        self.title_lengths: list[int] = []
        self.idf: dict[str, float] = {}
        self._build_index()
        self.calculator = ChallanCalculator()
        self.llm = LocalLLMRuntime()
        self._answer_cache: OrderedDict[tuple[str, str, str, str], dict[str, Any]] = OrderedDict()
        self._cache_lock = threading.Lock()

    def health(self) -> dict[str, Any]:
        status = self.llm.status()
        jurisdictions = sorted({p.jurisdiction for p in self.passages})
        return {
            "passages": len(self.passages),
            "index_file": str(self.index_file),
            "jurisdictions": jurisdictions,
            "model": asdict(status),
            "retrieval": {
                "engine": "jurisdiction-filtered-bm25-plus",
                "unicode": True,
                "multilingual_query_expansion": True,
                "answer_cache_size": len(self._answer_cache),
            },
        }

    def search(self, query: str, jurisdiction: str = "india_national", k: int = 6) -> list[dict[str, Any]]:
        results, _ = self.search_with_diagnostics(query, jurisdiction=jurisdiction, k=k)
        return results

    def search_with_diagnostics(
        self, query: str, jurisdiction: str = "india_national", k: int = 6
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        started = time.perf_counter()
        terms, concepts = expand_query(query)
        if not terms:
            return [], {"latency_ms": 0.0, "query_terms": [], "concepts": [], "candidates": 0}
        scores: list[tuple[float, Passage]] = []
        avg_len = sum(self.doc_lengths) / max(1, len(self.doc_lengths))
        avg_title_len = sum(self.title_lengths) / max(1, len(self.title_lengths))
        allowed = self._allowed_jurisdictions(jurisdiction)
        for idx, passage in enumerate(self.passages):
            if passage.jurisdiction not in allowed:
                continue
            body_score = self._bm25_score(terms, self.body_terms[idx], self.doc_lengths[idx], avg_len)
            title_score = self._bm25_score(terms, self.title_terms[idx], self.title_lengths[idx], avg_title_len)
            tag_score = sum(self.idf.get(term, 0.0) for term in set(terms) if term in self.tag_terms[idx])
            concept_score = sum(2.4 for concept in concepts if concept in passage.tags)
            score = body_score + (1.65 * title_score) + (1.25 * tag_score) + concept_score
            if passage.jurisdiction == jurisdiction:
                score *= 1.38
            elif passage.jurisdiction == "bimstec":
                score *= 0.92
            elif passage.jurisdiction == "global":
                score *= 0.78
            else:
                score *= 1.16
            if passage.verified:
                score *= 1.14
            else:
                score *= 0.84
            if passage.source_type in {"official_law", "official_government", "official_public_health"}:
                score *= 1.16
            if score >= 0.2:
                scores.append((score, passage))
        scores.sort(key=lambda item: item[0], reverse=True)
        results: list[dict[str, Any]] = []
        per_source: Counter[str] = Counter()
        fingerprints: set[str] = set()
        for score, passage in scores:
            fingerprint = normalize_space(passage.text).casefold()[:180]
            if fingerprint in fingerprints or per_source[passage.source_title] >= 1:
                continue
            fingerprints.add(fingerprint)
            per_source[passage.source_title] += 1
            results.append({"score": round(score, 3), **asdict(passage)})
            if len(results) >= k:
                break
        diagnostics = {
            "engine": "jurisdiction-filtered-bm25-plus",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "query_terms": terms[:24],
            "concepts": sorted(concepts),
            "candidates": len(scores),
            "results": len(results),
        }
        return results, diagnostics

    def answer(self, message: str, jurisdiction: str = "india_national", language: str = "English") -> dict[str, Any]:
        inferred = jurisdiction_from_text(message, jurisdiction)
        jurisdiction = inferred or jurisdiction
        model_mode = self.llm.status().mode
        cache_key = (normalize_space(message).casefold(), jurisdiction, language.casefold(), model_mode)
        cached = self._cache_get(cache_key)
        if cached is not None:
            cached["cache_hit"] = True
            return cached
        retrieved, retrieval = self.search_with_diagnostics(message, jurisdiction=jurisdiction, k=5)
        fine = self._maybe_calculate(message, jurisdiction)
        prompt = self._prompt(message, jurisdiction, language, retrieved, fine)
        use_model = bool(retrieved) and not self._fast_structured_answer(message, fine)
        generated = self.llm.generate(prompt) if use_model else None
        generation_guard = "not_requested"
        if generated:
            generated = generated.replace("overspending", "overspeeding")
            generation_guard = "passed" if self._generation_is_grounded(generated, retrieved, fine) else "rejected"
            if generation_guard == "rejected":
                generated = None
        if generated:
            answer_text = generated
            mode = "generative-rag"
        else:
            answer_text = self._extractive_answer(message, jurisdiction, retrieved, fine)
            mode = "extractive-rag"
        response = {
            "answer": answer_text,
            "mode": mode,
            "jurisdiction": jurisdiction,
            "language": language,
            "cache_hit": False,
            "retrieval": retrieval,
            "generation_guard": generation_guard,
            "citations": [
                {
                    "title": item["source_title"],
                    "url": item["source_url"],
                    "passage": item["title"],
                    "country": item["country"],
                    "verified": item["verified"],
                    "review_status": item["review_status"],
                    "score": item["score"],
                }
                for item in retrieved
            ],
            "fine": fine,
            "model": asdict(self.llm.status()),
        }
        self._cache_put(cache_key, response)
        return response

    def _maybe_calculate(self, message: str, jurisdiction: str) -> dict[str, Any] | None:
        lowered = message.lower()
        _, concepts = expand_query(message)
        fine_terms = ["fine", "challan", "penalty", "how much", "ticket"]
        offence_terms = ["speed", "helmet", "seat", "drunk", "drink", "license", "licence", "phone", "insurance", "registration"]
        if not concepts and not any(term in lowered for term in fine_terms + offence_terms):
            return None
        vehicle = "light_motor_vehicle"
        if "no_helmet" in concepts or "motorcycle" in lowered or "bike" in lowered or "two wheeler" in lowered or "scooter" in lowered:
            vehicle = "two_wheeler"
        if "truck" in lowered or "heavy" in lowered or "bus" in lowered:
            vehicle = "heavy_vehicle"
        offence_query = sorted(concepts)[0] if concepts else lowered
        result = self.calculator.calculate(jurisdiction, offence_query, vehicle)
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
                lines.append(f"Legal basis: {fine['legal_basis'].rstrip('.')}.")
            if fine.get("consequences"):
                lines.append("Possible consequences: " + "; ".join(item.rstrip(".") for item in fine["consequences"]) + ".")
            if fine.get("caveats"):
                lines.append("Caveat: " + " ".join(fine["caveats"]))

        if retrieved:
            lines.append("Grounded answer:")
            for item in retrieved[:2]:
                snippet = self._relevant_snippet(message, item["text"])
                lines.append(f"- {snippet} [{item['source_title']}]")
        else:
            lines.append("I do not have enough local source material to answer that safely yet.")

        tip = self._safety_tip(message)
        if tip:
            lines.append(f"Safety coach: {tip}")
        lines.append("This is an informational estimate, not legal advice. Verify urgent or disputed matters with the local traffic authority.")
        return "\n".join(lines)

    @staticmethod
    def _relevant_snippet(message: str, text: str, max_chars: int = 300) -> str:
        clean = normalize_space(text)
        if len(clean) <= max_chars:
            return clean

        query_tokens, concepts = expand_query(message)
        needles = [
            alias
            for concept in concepts
            for alias in QUERY_ALIASES.get(concept, ())
            if len(alias) >= 4
        ]
        needles.extend(token for token in query_tokens if len(token) >= 4)

        folded = clean.casefold()
        matches = [folded.find(needle.casefold()) for needle in needles]
        matches = [position for position in matches if position >= 0]
        focus = min(matches) if matches else 0

        start = max(0, focus - max_chars // 3)
        for separator in (" -", ". ", "। ", "။ "):
            boundary = clean.rfind(separator, start, focus + 1)
            if boundary >= start:
                start = boundary + len(separator)
        end = min(len(clean), start + max_chars)
        for separator in (" -", ". ", "। ", "။ "):
            boundary = clean.find(separator, focus, end)
            if boundary > focus:
                end = min(end, boundary + (1 if separator == ". " else 0))

        snippet = normalize_space(clean[start:end])
        if start > 0:
            snippet = "..." + snippet
        if end < len(clean):
            snippet += "..."
        return snippet

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
            f"[S{index}] {item['source_title']} | status={item['review_status']}\n"
            f"{normalize_space(item['text'])[:500]}"
            for index, item in enumerate(retrieved[:2], start=1)
        )
        fine_context = None
        if fine:
            fine_context = {
                key: fine.get(key)
                for key in ("status", "amount_display", "legal_basis", "consequences", "caveats")
                if fine.get(key)
            }
        fine_text = json.dumps(fine_context, ensure_ascii=True) if fine_context else "No structured fine estimate."
        return (
            "Answer the road-law question using only the supplied sources and fine record. "
            "Be concise, use the selected language, and cite claims as [S1], [S2], etc. "
            "Write a direct answer and never repeat source headers, metadata, or status fields. "
            "Never invent a fine, section, limit, phone number, or enforcement outcome. "
            "When a record says needs_review, clearly say the amount requires official verification. "
            "If evidence is insufficient, say what is missing. Do not provide legal advice. /no_think\n\n"
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
            body = Counter(tokenize(passage.text))
            title = Counter(tokenize(passage.title))
            tags = Counter(tokenize(" ".join(passage.tags)))
            combined = body + title + tags
            self.body_terms.append(body)
            self.title_terms.append(title)
            self.tag_terms.append(tags)
            self.doc_terms.append(combined)
            self.doc_lengths.append(sum(body.values()))
            self.title_lengths.append(sum(title.values()))
            for term in combined:
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

    @staticmethod
    def _allowed_jurisdictions(jurisdiction: str) -> set[str]:
        allowed = {jurisdiction, "global", "bimstec"}
        if jurisdiction == "delhi":
            allowed.add("india_national")
        return allowed

    def _cache_get(self, key: tuple[str, str, str, str]) -> dict[str, Any] | None:
        with self._cache_lock:
            value = self._answer_cache.get(key)
            if value is None:
                return None
            self._answer_cache.move_to_end(key)
            return deepcopy(value)

    def _cache_put(self, key: tuple[str, str, str, str], value: dict[str, Any]) -> None:
        with self._cache_lock:
            self._answer_cache[key] = deepcopy(value)
            self._answer_cache.move_to_end(key)
            while len(self._answer_cache) > 100:
                self._answer_cache.popitem(last=False)

    @staticmethod
    def _fast_structured_answer(message: str, fine: dict[str, Any] | None) -> bool:
        if not fine or fine.get("status") in {"unknown_offence", "unknown_vehicle_class"}:
            return False
        lowered = message.casefold()
        return len(message) <= 220 and any(term in lowered for term in ("fine", "challan", "penalty", "how much", "ปรับ", "জরিমানা"))

    @staticmethod
    def _generation_is_grounded(
        generated: str, retrieved: list[dict[str, Any]], fine: dict[str, Any] | None
    ) -> bool:
        if "| status=" in generated.casefold() or "fine estimate:" in generated.casefold():
            return False
        evidence = " ".join(item["text"] for item in retrieved[:2]) + " " + json.dumps(fine or {}, ensure_ascii=False)
        evidence_folded = evidence.casefold().replace(",", "")
        without_citations = re.sub(r"\[S\d+\]", "", generated)
        high_stakes_numbers = re.findall(
            r"(?:[$฿₹]|\b(?:thb|inr|bdt|npr|lkr|mmk|btn)\s*)\d[\d,.]*"
            r"|\b\d[\d,.]*\s*(?:km/h|kph|%|percent|mg|g/l|baht|rupees?|taka|kyat|ngultrum)\b",
            without_citations,
            flags=re.IGNORECASE,
        )
        for claim in high_stakes_numbers:
            number_match = re.search(r"\d[\d,.]*", claim)
            number = number_match.group(0).replace(",", "") if number_match else ""
            if number and number not in evidence_folded:
                return False
        risky_terms = (
            "imprison",
            "prison",
            "arrest",
            "suspend",
            "revok",
            "confiscat",
            "driver point",
            "court",
        )
        output_folded = generated.casefold()
        if any(term in output_folded and term not in evidence_folded for term in risky_terms):
            return False
        citation_numbers = [int(value) for value in re.findall(r"\[S(\d+)\]", generated)]
        return bool(citation_numbers) and max(citation_numbers) <= min(2, len(retrieved))
