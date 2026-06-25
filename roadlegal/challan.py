from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import SEED_DIR
from .text import normalize_space


FINE_FILE = SEED_DIR / "fine_schedule.json"


OFFENCE_ALIASES = {
    "speed": "overspeeding",
    "speeding": "overspeeding",
    "overspeed": "overspeeding",
    "helmet": "no_helmet",
    "no helmet": "no_helmet",
    "seat belt": "no_seatbelt",
    "seatbelt": "no_seatbelt",
    "drunk": "drink_driving",
    "drink": "drink_driving",
    "alcohol": "drink_driving",
    "license": "no_license",
    "licence": "no_license",
    "phone": "mobile_phone",
    "mobile": "mobile_phone",
    "insurance": "no_insurance",
    "registration": "no_registration",
}


@dataclass
class FineResult:
    jurisdiction: str
    offence: str
    vehicle_class: str
    status: str
    amount_display: str
    legal_basis: str
    consequences: list[str]
    caveats: list[str]
    source: str | None


class ChallanCalculator:
    def __init__(self, fine_file: Path = FINE_FILE) -> None:
        self.fine_file = fine_file
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.fine_file.exists():
            return {"jurisdictions": {}}
        with self.fine_file.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def jurisdictions(self) -> list[dict[str, Any]]:
        items = []
        for key, value in self.data.get("jurisdictions", {}).items():
            items.append({"id": key, "name": value.get("name", key), "country": value.get("country", "")})
        return sorted(items, key=lambda item: item["name"])

    def offences(self, jurisdiction: str) -> list[dict[str, Any]]:
        jurisdiction_data = self._jurisdiction_data(jurisdiction)
        output = []
        for key, value in jurisdiction_data.get("offences", {}).items():
            output.append({"id": key, "label": value.get("label", key), "vehicle_classes": sorted(value.get("vehicles", {}).keys())})
        return output

    def calculate(self, jurisdiction: str, offence: str, vehicle_class: str = "light_motor_vehicle") -> FineResult:
        jurisdiction_key = self._normalize_jurisdiction(jurisdiction)
        offence_key = self._normalize_offence(offence)
        vehicle_key = normalize_space(vehicle_class).lower().replace(" ", "_") or "light_motor_vehicle"

        jurisdiction_data = self._jurisdiction_data(jurisdiction_key)
        offence_data = jurisdiction_data.get("offences", {}).get(offence_key)
        if not offence_data:
            return FineResult(
                jurisdiction=jurisdiction_key,
                offence=offence_key,
                vehicle_class=vehicle_key,
                status="unknown_offence",
                amount_display="No verified fine in the local schedule.",
                legal_basis="No local structured fine record yet.",
                consequences=[],
                caveats=["Ask a more specific question or update data/seed/fine_schedule.json from official notices."],
                source=None,
            )

        vehicle_data = offence_data.get("vehicles", {}).get(vehicle_key) or offence_data.get("vehicles", {}).get("any")
        if not vehicle_data:
            available = ", ".join(sorted(offence_data.get("vehicles", {}).keys()))
            return FineResult(
                jurisdiction=jurisdiction_key,
                offence=offence_key,
                vehicle_class=vehicle_key,
                status="unknown_vehicle_class",
                amount_display=f"No verified amount for {vehicle_key}. Available: {available or 'none'}.",
                legal_basis=offence_data.get("legal_basis", ""),
                consequences=offence_data.get("consequences", []),
                caveats=offence_data.get("caveats", []),
                source=offence_data.get("source"),
            )

        amount_display = vehicle_data.get("amount_display")
        if not amount_display:
            currency = vehicle_data.get("currency", "")
            minimum = vehicle_data.get("fine_min")
            maximum = vehicle_data.get("fine_max")
            if minimum and maximum and minimum != maximum:
                amount_display = f"{currency}{minimum:,} - {currency}{maximum:,}"
            elif minimum:
                amount_display = f"{currency}{minimum:,}"
            else:
                amount_display = "Amount requires local verification."

        return FineResult(
            jurisdiction=jurisdiction_key,
            offence=offence_key,
            vehicle_class=vehicle_key,
            status=vehicle_data.get("status", "verified"),
            amount_display=amount_display,
            legal_basis=offence_data.get("legal_basis", ""),
            consequences=vehicle_data.get("consequences", offence_data.get("consequences", [])),
            caveats=vehicle_data.get("caveats", offence_data.get("caveats", [])),
            source=offence_data.get("source"),
        )

    def _jurisdiction_data(self, jurisdiction: str) -> dict[str, Any]:
        jurisdiction_key = self._normalize_jurisdiction(jurisdiction)
        jurisdictions = self.data.get("jurisdictions", {})
        return jurisdictions.get(jurisdiction_key) or jurisdictions.get("india_national") or {}

    def _normalize_jurisdiction(self, jurisdiction: str) -> str:
        key = normalize_space(jurisdiction).lower().replace(" ", "_")
        if not key:
            return "india_national"
        aliases = self.data.get("aliases", {})
        return aliases.get(key, key)

    def _normalize_offence(self, offence: str) -> str:
        key = normalize_space(offence).lower().replace("_", " ")
        if key in OFFENCE_ALIASES:
            return OFFENCE_ALIASES[key]
        for alias, canonical in OFFENCE_ALIASES.items():
            if alias in key:
                return canonical
        return key.replace(" ", "_")
