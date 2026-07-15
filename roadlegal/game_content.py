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
            "question": "In India, why does the challan / ticket calculator ask for vehicle class on overspeeding?",
            "options": ["Fines can differ by light and heavy vehicle class", "Vehicle class never matters", "Only vehicle colour matters"],
            "answer": 0,
            "explanation": "The structured calculator separates light, two-wheeler, and heavy vehicle cases where the law or compounding schedule differs.",
        },
        {
            "id": "india_helmet_1",
            "question": "An adult passenger joins a short two-wheeler trip in India without a helmet. What should the rider do?",
            "options": ["Wait until the passenger has a fastened helmet", "Continue below 20 km/h", "Use side streets to avoid enforcement"],
            "answer": 0,
            "explanation": "Protective-headgear duties and injury risk apply to short trips too; the safe choice is a correctly fastened helmet before moving.",
        },
        {
            "id": "india_challan_1",
            "question": "An India e-challan looks unfamiliar. What is the strongest first check?",
            "options": ["Verify it on the official Parivahan or local police portal", "Pay through a link in an unknown message", "Ignore every camera challan"],
            "answer": 0,
            "explanation": "Use an official portal to verify vehicle, offence, location, amount, and payment status before acting.",
        },
    ],
    "delhi": [
        {
            "id": "delhi_speed_1",
            "question": "Delhi scenario: a camera challan claims overspeeding. What should you check?",
            "options": ["Vehicle number, location, measured speed, road limit, and e-challan portal status", "Only the colour of the vehicle", "Ignore it until stopped again"],
            "answer": 0,
            "explanation": "Camera/enforcement records should be checked against the official e-challan details and local speed limit.",
        },
        {
            "id": "delhi_air_quality_1",
            "question": "A Delhi traveller hears that temporary vehicle restrictions may be active. What should they do?",
            "options": ["Check current official traffic and transport notices before departure", "Assume last year's rule is unchanged", "Rely only on a social-media message"],
            "answer": 0,
            "explanation": "Temporary restrictions can change quickly; an official current notice is the proper source.",
        },
    ],
    "bangladesh_national": [
        {
            "id": "bangladesh_review_1",
            "question": "Bangladesh fine data is marked review-needed. What should RoadLegal do?",
            "options": ["Cite the source and avoid inventing a final amount", "Guess a fine", "Copy another country's schedule"],
            "answer": 0,
            "explanation": "Legal accuracy beats false certainty. RoadLegal should flag schedules that still need BRTA/legal review.",
        },
        {
            "id": "bangladesh_documents_1",
            "question": "Before a commercial road trip in Bangladesh, which check is most complete?",
            "options": ["Licence, registration, fitness, route permit, and required insurance evidence", "Only the driver's phone", "Only the number plate"],
            "answer": 0,
            "explanation": "Vehicle and trip type can require several driver, vehicle, fitness, and permit documents.",
        },
    ],
    "bhutan_national": [
        {
            "id": "bhutan_mountain_1",
            "question": "Fog reduces visibility on a mountain road in Bhutan. What is the safest response?",
            "options": ["Slow down, increase distance, and stop safely if visibility collapses", "Follow the centre line at normal speed", "Overtake before the next bend"],
            "answer": 0,
            "explanation": "Mountain geometry, weather, and limited sight distance require a speed well below the maximum when conditions deteriorate.",
        },
        {
            "id": "bhutan_documents_1",
            "question": "A cross-border vehicle enters Bhutan. What should be checked before continuing?",
            "options": ["Entry authority, licence, registration, insurance, permits, and route conditions", "Only fuel level", "Only a hotel address"],
            "answer": 0,
            "explanation": "Cross-border driving can involve vehicle-entry and route requirements in addition to ordinary driver documents.",
        },
    ],
    "nepal_national": [
        {
            "id": "nepal_descent_1",
            "question": "A driver begins a long steep descent in Nepal. Which technique is safest?",
            "options": ["Use an appropriate lower gear and preserve braking capacity", "Coast in neutral", "Hold the brakes continuously at high speed"],
            "answer": 0,
            "explanation": "Controlled gearing and speed help prevent brake overheating on long descents.",
        },
        {
            "id": "nepal_cross_border_1",
            "question": "Before taking a rented vehicle across a Nepal border, what must be confirmed?",
            "options": ["Rental authority, border permission, licence acceptance, insurance, and vehicle documents", "Only the rental price", "A verbal promise from another traveller"],
            "answer": 0,
            "explanation": "Rental and insurance agreements may restrict border travel even when the driver holds a licence.",
        },
    ],
    "sri_lanka_national": [
        {
            "id": "sri_lanka_licence_1",
            "question": "A visitor plans to drive in Sri Lanka. What should be confirmed before collecting the rental car?",
            "options": ["Licence recognition or endorsement, rental authority, and insurance", "Only passport expiry", "Only the vehicle colour"],
            "answer": 0,
            "explanation": "Visitors should confirm that their driving credential is accepted and that the rental and insurance cover them.",
        },
        {
            "id": "sri_lanka_crossing_1",
            "question": "Pedestrians are waiting near an uncontrolled crossing in Sri Lanka. What is the lowest-risk choice?",
            "options": ["Slow early, scan both sides, and be ready to stop", "Accelerate before they step out", "Sound the horn and keep speed"],
            "answer": 0,
            "explanation": "Early speed reduction creates time to detect and yield safely to vulnerable road users.",
        },
    ],
    "myanmar_national": [
        {
            "id": "myanmar_traffic_side_1",
            "question": "What deserves special attention when beginning to drive in Myanmar?",
            "options": ["Right-hand traffic, vehicle blind spots, turns, and overtaking position", "Assume all vehicles place the driver on the same side", "Follow the largest vehicle closely"],
            "answer": 0,
            "explanation": "Myanmar uses right-hand traffic while vehicle layouts can vary, so sight lines and overtaking need deliberate adjustment.",
        },
        {
            "id": "myanmar_source_1",
            "question": "A Myanmar fine amount cannot be verified from the packaged official material. What should RoadLegal display?",
            "options": ["The rule and source status, without inventing an amount", "A neighbouring country's fine", "A random estimate"],
            "answer": 0,
            "explanation": "A cautious, traceable answer is more legally useful than unsupported precision.",
        },
    ],
}


def quiz_for(jurisdiction: str) -> dict:
    country_questions = COUNTRY_QUESTIONS.get(jurisdiction, [])
    questions = country_questions + COMMON_QUESTIONS
    return {"jurisdiction": jurisdiction, "questions": questions}
