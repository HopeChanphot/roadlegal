from __future__ import annotations


COMMON_QUESTIONS = [
    {
        "id": "common_helmet_1",
        "question": "A motorcycle passenger says the trip is short and refuses a helmet. What is the safest response?",
        "options": ["Ride only after everyone wears a fastened helmet", "Ride slowly without a helmet", "Use a helmet only on highways"],
        "answer": 0,
        "explanation": "Helmet use is both a legal requirement in many BIMSTEC jurisdictions and a major injury-prevention measure.",
    },
    {
        "id": "common_speed_1",
        "question": "Why does RoadLegal warn strongly about small speed increases?",
        "options": ["Higher speed raises crash likelihood and injury severity", "Speed only matters on expressways", "Speed is only a fuel-efficiency issue"],
        "answer": 0,
        "explanation": "WHO guidance links higher average speed to both crash probability and fatal/serious injury risk.",
    },
    {
        "id": "common_documents_1",
        "question": "A traffic officer asks for licence and registration documents. What should a driver do?",
        "options": ["Follow the lawful document-production process", "Ignore the request", "Only show documents after a crash"],
        "answer": 0,
        "explanation": "Traffic laws commonly require drivers to produce licence and registration evidence when legally requested.",
    },
]


COUNTRY_QUESTIONS = {
    "thailand_national": [
        {
            "id": "thailand_left_side_1",
            "question": "You enter Thailand from a country where traffic habits feel different. What should you check first?",
            "options": ["Drive on the left and scan carefully before turns", "Use the right lane as the default", "Follow only the vehicle in front"],
            "answer": 0,
            "explanation": "Thailand uses left-side traffic. Cross-border drivers should reset lane, turn, mirror, and pedestrian-scanning habits.",
        },
        {
            "id": "thailand_scooter_market_1",
            "question": "Thailand scenario: your passenger refuses a helmet for a short scooter ride to a night market. What wins the safety round?",
            "options": ["Wait until both people wear fastened helmets", "Ride slowly with only the driver wearing a helmet", "Avoid police checkpoints and continue"],
            "answer": 0,
            "explanation": "For motorcycle trips, the safe and legally cautious choice is fastened helmets for rider and passenger.",
        },
        {
            "id": "thailand_monsoon_1",
            "question": "Thailand scenario: monsoon rain starts on a highway. The posted limit is high, but visibility is poor. What should you do?",
            "options": ["Slow down and increase following distance", "Keep the posted maximum speed", "Brake sharply whenever spray appears"],
            "answer": 0,
            "explanation": "A posted limit is a maximum, not a target. Rain, spray, and low visibility require slower speed and more distance.",
        },
        {
            "id": "thailand_tourist_docs_1",
            "question": "A tourist rents a car in Thailand. Which checklist is strongest before driving?",
            "options": ["Accepted licence, passport/ID, rental papers, registration, and insurance", "Only a hotel booking", "A photo of a licence saved online"],
            "answer": 0,
            "explanation": "Travellers should carry accepted driving credentials and vehicle/rental/insurance evidence for enforcement or crash situations.",
        },
        {
            "id": "thailand_drink_driving_1",
            "question": "After dinner in Bangkok, a driver feels 'mostly fine' after alcohol. What is the best decision?",
            "options": ["Do not drive; use a sober driver, taxi, or public transport", "Drive slowly in the left lane", "Drink coffee and wait five minutes"],
            "answer": 0,
            "explanation": "Drink-driving enforcement can involve testing and serious consequences. The safe choice is not to drive after alcohol.",
        },
    ],
    "india_national": [
        {
            "id": "india_speed_1",
            "question": "In India, why does the challan calculator ask for vehicle class on overspeeding?",
            "options": ["Fines can differ by light and heavy vehicle class", "Vehicle class never matters", "Only vehicle colour matters"],
            "answer": 0,
            "explanation": "The structured calculator separates light, two-wheeler, and heavy vehicle cases where the law or compounding schedule differs.",
        }
    ],
    "delhi": [
        {
            "id": "delhi_speed_1",
            "question": "Delhi scenario: a camera challan claims overspeeding. What should you check?",
            "options": ["Vehicle number, location, measured speed, road limit, and e-challan portal status", "Only the colour of the vehicle", "Ignore it until stopped again"],
            "answer": 0,
            "explanation": "Camera/enforcement records should be checked against the official e-challan details and local speed limit.",
        }
    ],
    "bangladesh_national": [
        {
            "id": "bangladesh_review_1",
            "question": "Bangladesh fine data is marked review-needed. What should RoadLegal do?",
            "options": ["Cite the source and avoid inventing a final amount", "Guess a fine", "Copy another country's schedule"],
            "answer": 0,
            "explanation": "Legal accuracy beats false certainty. RoadLegal should flag schedules that still need BRTA/legal review.",
        }
    ],
}


def quiz_for(jurisdiction: str) -> dict:
    country_questions = COUNTRY_QUESTIONS.get(jurisdiction, [])
    questions = country_questions + COMMON_QUESTIONS
    return {"jurisdiction": jurisdiction, "questions": questions}
