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

TOPIC_KEYWORDS = {
    "overspeeding": ["speed", "speeding", "overspeeding", "speed limit", "speed camera", "driving too fast"],
    "no_helmet": ["helmet", "no helmet", "motorcycle helmet", "bike helmet", "rider", "passenger helmet"],
    "no_seatbelt": ["seat belt", "seatbelt", "safety belt", "rear seat belt", "buckle"],
    "drink_driving": ["drink driving", "drunk driving", "alcohol", "intoxicated", "breath test", "bac"],
    "mobile_phone": ["mobile phone", "cell phone", "phone while driving", "texting", "hands free", "distracted driving"],
    "no_license": ["driving licence", "driver licence", "driver license", "no licence", "no license", "expired licence", "international driving permit", "idp"],
    "no_insurance": ["insurance", "uninsured", "no insurance", "third party insurance", "insurance certificate"],
    "no_registration": ["registration", "unregistered vehicle", "number plate", "license plate", "registration certificate"],
    "dangerous_driving": ["dangerous driving", "reckless driving", "careless driving", "street racing", "stunt driving", "road rage"],
    "parking": ["parking", "no parking", "illegal parking", "tow", "towing", "clamp", "parked vehicle"],
    "traffic_signals": ["traffic signal", "traffic light", "red light", "amber light", "stop line", "signal violation"],
    "pedestrian_safety": ["pedestrian", "crosswalk", "zebra crossing", "footpath", "school crossing", "give way to people"],
    "child_restraints": ["child seat", "child restraint", "baby seat", "booster seat", "children in car", "child passenger"],
    "vehicle_condition": ["vehicle fitness", "inspection", "roadworthy", "tyre", "tire", "brake", "vehicle lights", "maintenance"],
    "fatigue": ["fatigue", "drowsy", "sleepy", "tired", "tired driver", "too tired to drive", "rest break", "falling asleep"],
    "weather": ["rain", "fog", "flood", "monsoon", "bad weather", "low visibility", "wet road"],
    "road_signs": ["road sign", "traffic sign", "signage", "road marking", "warning sign", "regulatory sign"],
    "overtaking": ["overtake", "overtaking", "passing vehicle", "blind curve", "solid line", "no overtaking"],
    "road_rules_overview": ["traffic rules", "road rules", "traffic law", "driving rules", "what should i know", "driving in"],
    "documents": ["documents", "document checklist", "what to carry", "paperwork", "vehicle papers", "permit documents"],
    "cross_border": ["cross border", "cross-border", "border crossing", "tourist driver", "traveller", "traveler", "foreign vehicle", "road trip"],
    "emergency": ["emergency", "ambulance", "police help", "emergency number", "breakdown", "injured person"],
    "accident_duties": ["after accident", "after crash", "road collision", "collision duties", "hit and run", "report accident", "exchange details", "crash scene"],
    "ticket_payment": ["pay challan", "pay ticket", "pay fine", "appeal ticket", "dispute fine", "court notice", "official payment", "ticket receipt"],
    "scenario": ["scenario", "quiz", "challenge", "game", "practice question"],
}

TOPICS.update(
    {
        "no_insurance": {
            "title": "Vehicle insurance requirement",
            "vehicle": "any",
            "rule": "Carry the motor-vehicle insurance or financial-responsibility evidence required by current local law; policy scope, digital proof, expiry, and cross-border recognition must be checked.",
            "actions": [
                "Confirm that the policy is active for the driver, vehicle, journey, and country.",
                "Keep legally accepted proof available for enforcement and crash reporting.",
                "Contact the insurer promptly after a collision and follow the policy reporting process.",
            ],
            "safety": "Insurance does not prevent a crash, but it supports victim compensation and responsible post-crash recovery.",
        },
        "no_registration": {
            "title": "Vehicle registration and number plates",
            "vehicle": "any",
            "rule": "A vehicle should have valid registration and display plates or identifiers as required; temporary, transferred, rented, imported, and cross-border vehicles can have additional conditions.",
            "actions": [
                "Check that registration details match the vehicle and have not expired.",
                "Keep plates visible and do not alter or obscure them.",
                "Carry rental, owner-authority, import, or border documents when they apply.",
            ],
            "safety": "Valid registration supports vehicle accountability, enforcement, insurance, and crash investigation.",
        },
        "dangerous_driving": {
            "title": "Dangerous and reckless driving",
            "vehicle": "any",
            "rule": "Racing, aggressive manoeuvres, deliberate risk-taking, and driving without reasonable care can trigger serious offences, court action, licence consequences, or vehicle seizure depending on local law and facts.",
            "actions": [
                "Leave space, avoid retaliation, and let an aggressive driver pass.",
                "Do not race, weave, tailgate, brake-check, or perform stunts on a public road.",
                "Report immediate danger from a safe location using the local police channel.",
            ],
            "safety": "Predictable, cooperative driving gives every road user more time to avoid a conflict.",
        },
        "parking": {
            "title": "Parking, stopping, and towing",
            "vehicle": "any",
            "rule": "Parking and stopping restrictions depend on signs, markings, road type, time, access needs, and local orders; obstruction, dangerous parking, and unauthorized spaces may lead to a ticket, clamp, or tow.",
            "actions": [
                "Read nearby signs and curb or road markings before leaving the vehicle.",
                "Keep crossings, junctions, emergency access, bus stops, and disability spaces clear.",
                "If towed, use the official police or municipal channel and keep payment receipts.",
            ],
            "safety": "Poorly parked vehicles can hide pedestrians and force cyclists or traffic into dangerous paths.",
        },
        "traffic_signals": {
            "title": "Traffic signals and stop lines",
            "vehicle": "any",
            "rule": "Obey traffic lights, lane signals, authorized officer directions, and stop lines; turning permissions and amber-light rules depend on the sign, signal phase, and local law.",
            "actions": [
                "Approach signals at a speed that allows a controlled stop.",
                "Stop before the marked line or crossing and check for pedestrians before turning.",
                "Follow an officer's lawful direction when it temporarily overrides a signal.",
            ],
            "safety": "Signal compliance prevents high-energy side-impact crashes and protects people in crossings.",
        },
        "pedestrian_safety": {
            "title": "Pedestrians and crossings",
            "vehicle": "any",
            "rule": "Drivers must use appropriate care around crossings, schools, markets, stopped public transport, and people already in or entering the road; exact right-of-way duties vary by local law and signal control.",
            "actions": [
                "Slow down early and be ready to stop where people may cross.",
                "Do not overtake a vehicle stopped for a crossing.",
                "Check mirrors and blind areas before turning, opening a door, or moving from rest.",
            ],
            "safety": "Lower impact speed greatly improves a pedestrian's chance of surviving a crash.",
        },
        "child_restraints": {
            "title": "Child passengers and restraints",
            "vehicle": "light_motor_vehicle",
            "rule": "Children should use an age-, height-, and weight-appropriate restraint fitted to the vehicle; mandatory ages, seating positions, taxi exemptions, and penalties depend on current local law.",
            "actions": [
                "Use a correctly installed child seat or booster suitable for the child.",
                "Follow the restraint and vehicle manufacturer instructions.",
                "Keep a rear-facing child away from an active frontal airbag.",
            ],
            "safety": "Adult seat belts alone do not fit small children correctly; appropriate restraints reduce ejection and severe injury.",
        },
        "vehicle_condition": {
            "title": "Vehicle fitness and roadworthiness",
            "vehicle": "any",
            "rule": "The vehicle must meet applicable fitness, inspection, equipment, tyre, brake, light, load, and emissions requirements; commercial and public-service vehicles often have additional duties.",
            "actions": [
                "Check tyres, brakes, lights, mirrors, wipers, fluids, and warning indicators before travel.",
                "Do not drive a vehicle with a safety-critical defect.",
                "Keep required inspection, fitness, pollution, and maintenance records current.",
            ],
            "safety": "Basic maintenance prevents loss-of-control, visibility, and stopping failures.",
        },
        "fatigue": {
            "title": "Fatigue and drowsy driving",
            "vehicle": "any",
            "rule": "A driver must remain fit and able to control the vehicle; commercial driving-hour and rest rules may impose specific limits beyond the general duty to drive safely.",
            "actions": [
                "Stop in a safe place when yawning, drifting, missing signs, or struggling to focus.",
                "Rest before long journeys and share driving when possible.",
                "Do not rely on music, open windows, or caffeine as a substitute for sleep.",
            ],
            "safety": "Severe fatigue slows reactions and can cause brief sleep episodes without warning.",
        },
        "weather": {
            "title": "Driving in rain, fog, flood, and poor visibility",
            "vehicle": "any",
            "rule": "The posted limit is a maximum; drivers must choose a lower safe speed and suitable lights, distance, and route when weather or road conditions reduce visibility or grip.",
            "actions": [
                "Slow down smoothly, increase following distance, and use suitable lights.",
                "Avoid sudden steering or braking on wet, loose, or flooded surfaces.",
                "Do not enter floodwater when depth, current, road edge, or surface condition is uncertain.",
            ],
            "safety": "Rain and fog reduce visibility and grip while increasing stopping distance.",
        },
        "road_signs": {
            "title": "Road signs and markings",
            "vehicle": "any",
            "rule": "Drivers must obey applicable regulatory signs, signals, lane arrows, and road markings; temporary work-zone or police directions can supersede normal arrangements.",
            "actions": [
                "Scan far enough ahead to read signs without abrupt manoeuvres.",
                "Treat unfamiliar signs cautiously and follow their shape, colour, symbol, and local meaning.",
                "Reduce speed around temporary signs, workers, diversions, and changed lane markings.",
            ],
            "safety": "Early sign recognition creates time for smooth, predictable decisions.",
        },
        "overtaking": {
            "title": "Overtaking and lane discipline",
            "vehicle": "any",
            "rule": "Overtake only where permitted and where there is enough sight distance, space, and speed difference; signs, solid lines, crossings, junctions, hills, curves, and local lane rules can prohibit passing.",
            "actions": [
                "Check mirrors, blind areas, signs, markings, and oncoming traffic before moving out.",
                "Pass with safe clearance and return only when the vehicle is clearly visible in the mirror.",
                "Never overtake into a blind curve, crest, crossing conflict, or insufficient gap.",
            ],
            "safety": "Unsafe overtaking creates high-speed head-on and side-swipe crashes.",
        },
        "road_rules_overview": {
            "title": "Essential road-law overview",
            "vehicle": "any",
            "rule": "Follow posted signs and signals, use the correct traffic side, carry accepted driver and vehicle documents, use occupant protection, avoid impairment and distraction, and adapt to current local restrictions.",
            "actions": [
                "Check the selected country's traffic side, licence acceptance, insurance, and emergency contacts.",
                "Use the prepared topic answers for speed, helmets, seat belts, tickets, documents, crossings, and emergencies.",
                "Verify an exact disputed fine or temporary local restriction with the cited authority.",
            ],
            "safety": "Safe road use combines legal compliance, attention, speed management, and protection for vulnerable road users.",
        },
    }
)


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
                "keywords": TOPIC_KEYWORDS[topic],
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
            "keywords": TOPIC_KEYWORDS["documents"],
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
            "keywords": TOPIC_KEYWORDS["cross_border"],
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
            "keywords": TOPIC_KEYWORDS["emergency"],
        }
        answers["accident_duties"] = {
            "topic": "accident_duties",
            "title": f"Duties after a road crash in {country}",
            "summary": "Stop safely, protect life, contact emergency services when needed, exchange required details, preserve evidence, and use the official reporting process; never leave to avoid responsibility.",
            "rules": [profile["framework"], "Exact reporting deadlines, police attendance, insurer notice, and vehicle-movement duties depend on current local law and crash severity."],
            "actions": [
                "Check for danger and injury, call the appropriate service, and give first aid only within your ability.",
                "Exchange identity, vehicle, licence, registration, insurance, and contact details as required.",
                "Photograph the scene when safe, note witnesses, and report through police and insurer channels.",
            ],
            "safety": "Prevent a secondary crash with a safe position, warning devices, and controlled traffic movement where possible.",
            "verification": profile["source_status"],
            "citations": _citations(profile),
            "keywords": TOPIC_KEYWORDS["accident_duties"],
        }
        answers["ticket_payment"] = {
            "topic": "ticket_payment",
            "title": f"Paying or disputing a traffic ticket in {country}",
            "summary": "Use only the official ticket, police, court, transport-authority, or government payment channel. Check the allegation and deadline before paying or requesting review, and keep the receipt.",
            "rules": [profile["framework"], "Payment, compounding, appeal, court referral, licence points, and late consequences depend on the issuing authority and current procedure."],
            "actions": [
                "Match the ticket number, vehicle, location, date, offence, amount, and issuing authority.",
                "Open the cited official portal yourself; do not trust an unsolicited payment link or personal account.",
                "Save the receipt and submit a dispute or court response before the stated deadline when appropriate.",
            ],
            "safety": "Deal with the notice while parked; never try to pay or dispute a ticket while driving.",
            "verification": profile["source_status"],
            "citations": _citations(profile, include_who=False),
            "keywords": TOPIC_KEYWORDS["ticket_payment"],
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
                "keywords": TOPIC_KEYWORDS["scenario"],
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
