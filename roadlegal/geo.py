from __future__ import annotations


COUNTRY_BOXES = [
    ("india_national", "India", 6.5, 37.1, 68.0, 97.5),
    ("bangladesh_national", "Bangladesh", 20.5, 26.8, 88.0, 92.8),
    ("bhutan_national", "Bhutan", 26.6, 28.4, 88.7, 92.2),
    ("nepal_national", "Nepal", 26.2, 30.5, 80.0, 88.3),
    ("sri_lanka_national", "Sri Lanka", 5.8, 10.0, 79.5, 82.1),
    ("thailand_national", "Thailand", 5.4, 20.6, 97.3, 105.7),
    ("myanmar_national", "Myanmar", 9.4, 28.6, 92.1, 101.2),
]


CITY_HINTS = {
    "delhi": "delhi",
    "new delhi": "delhi",
    "chennai": "tamil_nadu",
    "mumbai": "maharashtra",
    "kolkata": "west_bengal",
    "dhaka": "bangladesh_national",
    "kathmandu": "nepal_national",
    "thimphu": "bhutan_national",
    "colombo": "sri_lanka_national",
    "bangkok": "thailand_national",
    "yangon": "myanmar_national",
}


def geofence(lat: float, lon: float) -> dict[str, str | float | bool]:
    matches = []
    for jurisdiction, country, min_lat, max_lat, min_lon, max_lon in COUNTRY_BOXES:
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            area = (max_lat - min_lat) * (max_lon - min_lon)
            matches.append((area, jurisdiction, country))
    if matches:
        _, jurisdiction, country = sorted(matches, key=lambda item: item[0])[0]
        return {
            "matched": True,
            "jurisdiction": jurisdiction,
            "country": country,
            "confidence": 0.72,
            "note": "Country-level geofence. Add state/municipal polygons for production.",
        }
    return {
        "matched": False,
        "jurisdiction": "india_national",
        "country": "Unknown",
        "confidence": 0.0,
        "note": "Coordinates are outside the starter BIMSTEC bounding boxes.",
    }


def jurisdiction_from_text(value: str, fallback: str = "india_national") -> str:
    lowered = (value or "").lower()
    for hint, jurisdiction in CITY_HINTS.items():
        if hint in lowered:
            return jurisdiction
    return fallback
