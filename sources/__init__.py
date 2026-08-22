import json
import os

from .duckduckgo_source import search as ddg_search
from .reddit_source import search as reddit_search

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(_BASE, "config")

REGISTERED = {
    "reddit": reddit_search,
    "duckduckgo": ddg_search,
    "landing_page": lambda niche, cc: [],
}


def enabled_sources(country_code):
    cfg = json.load(open(os.path.join(CONFIG_DIR, "countries.json")))
    return cfg.get(country_code, {}).get("enabled_sources", ["duckduckgo"])


def fetch(niche, countries):
    out = []
    for cc in countries:
        for src in enabled_sources(cc):
            fn = REGISTERED.get(src)
            if not fn:
                continue
            try:
                out.extend(fn(niche, cc))
            except Exception:
                continue
    return out
