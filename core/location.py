"""Location normalization: turn free text into country/region/city + coords.

Uses config/countries.json city registry. Falls back to country-level if no city.
"""
import json
import os
import re

_CONFIG = None


def _cfg():
    global _CONFIG
    if _CONFIG is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "config", "countries.json")
        with open(path) as f:
            _CONFIG = json.load(f)
    return _CONFIG


COUNTRY_ALIASES = {
    "us": "US", "usa": "US", "united states": "US", "america": "US", "u.s.": "US",
    "uk": "GB", "united kingdom": "GB", "england": "GB", "britain": "GB", "great britain": "GB",
    "uae": "AE", "emirates": "AE", "united arab emirates": "AE",
    "canada": "CA",
    "australia": "AU", "au": "AU",
}


def normalize_location(text, hint_country=None):
    """Return a location dict.

    {country_code, country_name, region, city, normalized, lat, lon, language, confidence}
    confidence: 'city', 'region', 'country', or 'none'
    """
    if not text:
        text = ""
    t = text.lower().strip().rstrip(".")
    cfg = _cfg()

    # Clean prefixes like "r/cityname" or "in cityname"
    t = re.sub(r"^r/", "", t)
    t = re.sub(r"^(in|near|at)\s+", "", t)

    # 1) match city aliases across all countries
    for cc, country in cfg.items():
        for key, info in country["cities"].items():
            pats = [key.replace("_", " ")] + info.get("aliases", []) + [info["name"].lower()]
            for p in pats:
                if t == p or t.startswith(p) or p in t.split(",")[0]:
                    return {
                        "country_code": cc,
                        "country_name": country["name"],
                        "region": info["region"],
                        "city": info["name"],
                        "normalized": f"{info['name']}, {info['region']}, {country['name']}",
                        "lat": info["lat"],
                        "lon": info["lon"],
                        "language": country["language"],
                        "confidence": "city",
                    }

    # 2) country alias only
    for alias, cc in COUNTRY_ALIASES.items():
        if alias in t:
            country = cfg[cc]
            return {
                "country_code": cc, "country_name": country["name"],
                "region": None, "city": None, "normalized": country["name"],
                "lat": None, "lon": None,
                "language": country["language"], "confidence": "country",
            }

    # 3) hint country
    if hint_country and hint_country in cfg:
        country = cfg[hint_country]
        return {
            "country_code": hint_country, "country_name": country["name"],
            "region": None, "city": None, "normalized": country["name"],
            "lat": None, "lon": None,
            "language": country["language"], "confidence": "country",
        }

    return {
        "country_code": None, "country_name": None, "region": None, "city": None,
        "normalized": None, "lat": None, "lon": None,
        "language": None, "confidence": "none",
    }


def cities_for(country_code):
    return _cfg()[country_code]["cities"]


def radius_for(country_code):
    return _cfg()[country_code]["default_radius_km"]


def same_city(a, b):
    """Compare two normalized location dicts or city names."""
    if isinstance(a, dict):
        a = a.get("city")
    if isinstance(b, dict):
        b = b.get("city")
    if not a or not b:
        return None  # unknown -> needs review
    return a.strip().lower() == b.strip().lower()


def distance_km(lat1, lon1, lat2, lon2):
    import math
    if None in (lat1, lon1, lat2, lon2):
        return None
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))
