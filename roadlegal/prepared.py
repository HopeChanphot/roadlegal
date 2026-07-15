from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from .paths import WEB_DIR


STATIC_DATA_FILE = WEB_DIR / "static-data.json"


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", value.casefold(), flags=re.UNICODE)).strip()


@lru_cache(maxsize=1)
def _answer_packs() -> dict[str, Any]:
    if not STATIC_DATA_FILE.exists():
        return {}
    payload = json.loads(STATIC_DATA_FILE.read_text(encoding="utf-8"))
    return payload.get("offline_answers", {})


def clear_prepared_cache() -> None:
    _answer_packs.cache_clear()


def prepared_answer_count() -> int:
    return sum(len(pack.get("answers", {})) for pack in _answer_packs().values())


def _topic_score(query: str, query_tokens: set[str], topic: str, answer: dict[str, Any]) -> float:
    score = 0.0
    phrases = [topic.replace("_", " "), *answer.get("keywords", [])]
    for phrase in phrases:
        folded = _normalize(str(phrase))
        if not folded:
            continue
        phrase_tokens = set(folded.split())
        if f" {folded} " in f" {query} ":
            score += 5.0 + min(3.0, len(phrase_tokens))
            continue
        overlap = len(query_tokens & phrase_tokens)
        if len(phrase_tokens) > 1 and overlap == len(phrase_tokens):
            score += 3.0
        elif len(phrase_tokens) == 1 and overlap == 1 and len(folded) >= 4:
            score += 2.0
    return score


def match_prepared_answer(message: str, jurisdiction: str) -> tuple[str, dict[str, Any]] | None:
    pack = _answer_packs().get(jurisdiction) or _answer_packs().get("india_national")
    if not pack:
        return None
    answers = pack.get("answers", {})
    query = _normalize(message)
    query_tokens = set(query.split())
    ranked = sorted(
        (
            (_topic_score(query, query_tokens, topic, answer), topic, answer)
            for topic, answer in answers.items()
        ),
        reverse=True,
        key=lambda item: item[0],
    )
    if ranked and ranked[0][0] >= 2.0:
        _, topic, answer = ranked[0]
        return topic, answer
    overview = answers.get("road_rules_overview")
    return ("road_rules_overview", overview) if overview else None


def prepared_response(
    message: str,
    jurisdiction: str,
    language: str = "English",
    *,
    model: dict[str, Any] | None = None,
    reason: str = "prepared-answer fallback",
) -> dict[str, Any] | None:
    match = match_prepared_answer(message, jurisdiction)
    if not match:
        return None
    topic, entry = match
    localized = entry.get("localizations", {}).get(language, {})
    prepared = {**entry, **localized}
    prepared["citations"] = entry.get("citations", [])
    prepared["fine"] = entry.get("fine")
    lines = [prepared["title"], "", f"Quick answer: {prepared['summary']}", "", "Key rules:"]
    lines.extend(f"- {item}" for item in prepared.get("rules", []))
    lines.extend(["", "What to do:"])
    lines.extend(f"- {item}" for item in prepared.get("actions", []))
    if prepared.get("safety"):
        lines.extend(["", f"Safety note: {prepared['safety']}"])
    lines.extend(["", f"Source status: {prepared['verification']}"])
    return {
        "answer": "\n".join(lines),
        "prepared": prepared,
        "mode": "prepared-fallback",
        "jurisdiction": jurisdiction,
        "language": language,
        "citations": prepared.get("citations", []),
        "fine": prepared.get("fine"),
        "model": model or {},
        "live_fallback": True,
        "fallback_reason": reason,
        "matched_topic": topic,
    }


def needs_prepared_fallback(response: dict[str, Any]) -> bool:
    answer = str(response.get("answer", "")).strip()
    lowered = answer.casefold()
    model = response.get("model") or {}
    if model and model.get("loaded") is False:
        return True
    if len(answer) < 40:
        return True
    if "do not have enough" in lowered or "not have enough" in lowered:
        return True
    if not response.get("citations") and not response.get("fine"):
        return True
    return False


def apply_prepared_fallback(
    response: dict[str, Any], message: str, jurisdiction: str, language: str = "English"
) -> dict[str, Any]:
    if not needs_prepared_fallback(response):
        return response
    fallback = prepared_response(
        message,
        jurisdiction,
        language,
        model=response.get("model") or {},
        reason="Live model was unavailable or did not return a sufficiently grounded answer.",
    )
    return fallback or response
