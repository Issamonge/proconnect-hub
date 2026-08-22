"""Reddit adapter — PUBLIC posts via Reddit's own API (no scraping)."""
import json
import re
import time
import requests
from .common import as_intent

UA = {"User-Agent": "ProConnectHubIntent/1.0 (public API, no personal data)"}


def search(niche, country_code):
    """Use Reddit's public search.json endpoint; may return 403 from sandboxed IPs.
    When blocked, DDG fallback in pipeline still catches Reddit request threads.
    """
    niches = json.load(open("config/niches.json"))
    queries = niches.get(niche, {}).get("search_queries", {}).get("reddit", [])
    out = []
    for q in queries:
        params = {"q": q, "sort": "new", "t": "week", "limit": 10}
        try:
            r = requests.get("https://www.reddit.com/search.json",
                             params=params, headers=UA, timeout=15)
            if r.status_code != 200:
                continue
            for child in r.json().get("data", {}).get("children", []):
                d = child.get("data", {})
                permalink = "https://www.reddit.com" + d.get("permalink", "")
                if "reddit.com" not in permalink:
                    continue
                out.append({
                    "title": d.get("title", "")[:200],
                    "snippet": (d.get("selftext", "") or "")[:300],
                    "url": permalink,
                    "created_utc": d.get("created_utc"),
                    "subreddit": d.get("subreddit", ""),
                })
        except Exception:
            continue
        time.sleep(1)
    return out
