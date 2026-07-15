from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT))
from roadlegal.challan import ChallanCalculator  # noqa: E402
from roadlegal.game_content import quiz_for  # noqa: E402
from roadlegal.rag import INDEX_FILE, SEED_PASSAGES  # noqa: E402


OUT = ROOT / "web" / "static-data.json"
FINE_FILE = ROOT / "data" / "seed" / "fine_schedule.json"
OFFLINE_PROFILES_FILE = ROOT / "data" / "seed" / "offline_answer_profiles.json"

WHO_SOURCE = {
    "title": "WHO Road traffic injuries fact sheet",
    "url": "https://www.who.int/news-room/fact-sheets/detail/road-traffic-injuries",
    "verified": True,
}

TOPICS = {
    "overspeeding": {
        "title": "Speed limits and overspeeding",
        "vehicle": "light_motor_vehicle",
        "rule": "The posted limit, road class, vehicle class, location, measured speed, and repeat history can change the applicable offence or outcome.",
        "actions": [
            "Treat a posted limit as a maximum, not a target.",
            "Reduce speed for rain, darkness, pedestrians, schools, work zones, and poor road conditions.",
            "For a disputed ticket, check the vehicle, location, time, measured speed, posted limit, and official payment or review channel.",
        ],
        "safety": "Higher speed raises both crash probability and the severity of injury.",
    },
    "no_helmet": {
        "title": "Motorcycle helmet rule",
        "vehicle": "two_wheeler",
        "rule": "Riders and passengers should use a correctly fastened, standards-compliant helmet; exemptions and the exact penalty must come from current local law.",
        "actions": [
            "Do not begin the trip until the rider and passenger have fastened helmets.",
            "Replace a helmet after a severe impact or when its shell, strap, or buckle is damaged.",
            "Confirm that the licence, rental agreement, and insurance permit the motorcycle class being used.",
        ],
        "safety": "A quality, correctly worn helmet materially reduces fatal and serious head-injury risk.",
    },
    "no_seatbelt": {
        "title": "Seat-belt and occupant protection rule",
        "vehicle": "light_motor_vehicle",
        "rule": "Every occupant should use an available seat belt; covered seats, child restraints, exemptions, and penalties depend on current local law and vehicle configuration.",
        "actions": [
            "Buckle every occupant before the vehicle moves, including on short trips.",
            "Use an age- and size-appropriate child restraint where required and available.",
            "Do not place a child in front of an active airbag unless the vehicle instructions and law allow it.",
        ],
        "safety": "Seat belts reduce the risk of death and serious injury for vehicle occupants.",
    },
    "drink_driving": {
        "title": "Drink-driving and impairment",
        "vehicle": "any",
        "rule": "Do not drive after alcohol or impairing drugs. Testing thresholds, court referral, imprisonment, licence action, and repeat-offence consequences vary by jurisdiction and facts.",
        "actions": [
            "Use a sober driver, taxi, or public transport.",
            "Plan the trip home before drinking begins.",
            "Do not rely on coffee, food, or a short wait to remove impairment.",
        ],
        "safety": "Impairment begins before a driver necessarily feels drunk and reduces judgment, reaction, and hazard perception.",
    },
    "mobile_phone": {
        "title": "Mobile phone and distracted driving",
        "vehicle": "light_motor_vehicle",
        "rule": "Avoid handheld-phone use and any interaction that removes attention from driving; the exact offence definition and permitted hands-free use depend on current local law.",
        "actions": [
            "Set navigation and messages before moving.",
            "Stop in a lawful safe place before handling the phone.",
            "Keep attention on pedestrians, two-wheelers, junctions, and changing traffic signals.",
        ],
        "safety": "Visual, manual, and cognitive distraction can each delay recognition and braking.",
    },
    "no_license": {
        "title": "Driving-licence requirement",
        "vehicle": "any",
        "rule": "The driver must hold a valid licence accepted for the jurisdiction and vehicle class; learner, visitor, commercial, and endorsement conditions can differ.",
        "actions": [
            "Confirm that the licence is valid, unexpired, and covers the vehicle class.",
            "Travellers should verify whether an international permit, translation, endorsement, or local authorization is required.",
            "Do not drive when a licence is suspended, disqualified, or otherwise invalid.",
        ],
        "safety": "Licensing is intended to confirm minimum competence and accountability for the vehicle being driven.",
    },
}


def _citations(profile: dict, fine: dict | None = None, include_who: bool = True) -> list[dict]:
    citations = [
        {
            "title": profile["source_title"],
            "url": (fine or {}).get("source") or profile["source_url"],
            "verified": "Official" in profile["source_status"],
            "status": profile["source_status"],
        }
    ]
    if include_who:
        citations.append(WHO_SOURCE)
    return citations


def build_offline_answers(calculator: ChallanCalculator, profiles: dict, quizzes: dict) -> dict:
    answer_packs = {}
    for jurisdiction, profile in profiles.items():
        country = profile["country"]
        answers = {}
        for topic, config in TOPICS.items():
            fine = asdict(calculator.calculate(jurisdiction, topic, config["vehicle"]))
            has_amount = fine["status"] not in {"unknown_offence", "unknown_vehicle_class", "not_applicable"}
            if has_amount and fine["status"] == "verified":
                summary = f"The packaged verified schedule for {country} reports {fine['amount_display']} for this selected case."
            elif has_amount:
                summary = (
                    f"RoadLegal can explain the {country} rule, but the exact current amount is deliberately marked for official review: "
                    f"{fine['amount_display']}"
                )
            else:
                summary = (
                    f"RoadLegal has prepared guidance for {country}, but it does not claim an exact fine until a current official schedule "
                    "has completed legal review."
                )
            rules = [profile["framework"], config["rule"]]
            if fine.get("legal_basis") and not fine["legal_basis"].startswith("No local"):
                rules.insert(0, fine["legal_basis"])
            answer = {
                "topic": topic,
                "title": f"{config['title']} in {country}",
                "summary": summary,
                "rules": list(dict.fromkeys(rules)),
                "actions": config["actions"],
                "safety": config["safety"],
                "verification": profile["source_status"],
                "citations": _citations(profile, fine if has_amount else None),
                "fine": fine if has_amount else None,
            }
            localized = profile.get("thai_localizations", {}).get(topic)
            if localized:
                answer["localizations"] = {
                    "Thai": {
                        **localized,
                        "rules": [profile["framework"], config["rule"]],
                        "safety": config["safety"],
                        "verification": profile["source_status"],
                    }
                }
            answers[topic] = answer

        answers["documents"] = {
            "topic": "documents",
            "title": f"Driving document checklist for {country}",
            "summary": f"Carry original or legally accepted digital evidence for the driver, vehicle, insurance, and the specific journey in {country}.",
            "rules": [profile["framework"], profile["traveller_note"]],
            "actions": profile["documents"],
            "safety": "Confirm vehicle condition, insurance coverage, and emergency contacts before departure.",
            "verification": profile["source_status"],
            "citations": _citations(profile, include_who=False),
        }
        answers["cross_border"] = {
            "topic": "cross_border",
            "title": f"Cross-border readiness for {country}",
            "summary": f"Prepare for {profile['traffic_side'].lower()}, local enforcement, document recognition, insurance, and road-specific restrictions before entering {country}.",
            "rules": [profile["framework"], profile["traveller_note"]],
            "actions": [
                f"Reset lane, turn, mirror, and overtaking habits for {profile['traffic_side'].lower()}.",
                *profile["documents"],
                "Download or save official contacts and route information before crossing the border.",
            ],
            "safety": "Pause after crossing to re-check traffic side, signs, speed units, fuel, weather, and emergency plans.",
            "verification": profile["source_status"],
            "citations": _citations(profile),
        }
        answers["emergency"] = {
            "topic": "emergency",
            "title": f"Road emergency contacts for {country}",
            "summary": "Move out of live traffic if it is safe, protect the scene, call the appropriate emergency service, and document essential facts without obstructing responders.",
            "rules": [profile["framework"]],
            "actions": profile["emergency"] + [
                "Share the road, direction, landmark, injuries, hazards, and number of vehicles.",
                "Do not move an injured person unless immediate danger makes it necessary.",
            ],
            "safety": "Use hazard lights and warning devices only when it is safe to do so.",
            "verification": "Prepared emergency directory; confirm locally when connectivity is available",
            "citations": _citations(profile, include_who=False),
        }
        questions = quizzes.get(jurisdiction, {}).get("questions", [])
        if questions:
            scenario = questions[0]
            answers["scenario"] = {
                "topic": "scenario",
                "title": f"{country} safety scenario",
                "summary": scenario["question"],
                "rules": [f"Best choice: {scenario['options'][scenario['answer']]}", scenario["explanation"]],
                "actions": ["Identify the legal duty.", "Choose the lowest-risk action.", "Check how weather, road users, and enforcement change the decision."],
                "safety": "The full offline quiz keeps score and provides immediate explanations.",
                "verification": "Prepared RoadLegal learning scenario",
                "citations": [WHO_SOURCE],
            }
        answer_packs[jurisdiction] = {"profile": profile, "answers": answers}
    return answer_packs


def main() -> int:
    calculator = ChallanCalculator()
    index_file = INDEX_FILE if INDEX_FILE.exists() else SEED_PASSAGES
    passages = json.loads(index_file.read_text(encoding="utf-8"))
    fine_schedule = json.loads(FINE_FILE.read_text(encoding="utf-8"))
    offline_profiles = json.loads(OFFLINE_PROFILES_FILE.read_text(encoding="utf-8"))
    jurisdictions = calculator.jurisdictions()
    quizzes = {item["id"]: quiz_for(item["id"]) for item in jurisdictions}
    offline_answers = build_offline_answers(calculator, offline_profiles, quizzes)
    payload = {
        "health": {
            "passages": len(passages),
            "answer_topics": sum(len(pack["answers"]) for pack in offline_answers.values()),
            "offline_ready": True,
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
        "offline_answers": offline_answers,
        "passages": passages,
        "quizzes": quizzes,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote static demo data with {len(passages)} passages to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
