"""DuckDuckGo adapter using common.ddg, filtered to reddit.com request threads."""
import json
from .common import ddg, DDG_DIRECTORY_DENY

def search(niche, country_code):
    niches = json.load(open("config/niches.json"))
    queries = niches.get(niche, {}).get("search_queries", {}).get("duckduckgo", [])
    out = []
    for q in queries:
        for hit in ddg(q):
            if any(d in hit["url"].lower() for d in DDG_DIRECTORY_DENY + ["reddit.com"]):
                if "reddit.com" not in hit["url"].lower():
                    continue
            if "reddit.com/r/" in hit["url"].lower() and len(hit["url"].split("/")) < 7:
                continue
            if "reddit.com" not in hit["url"].lower() and not hit["url"].startswith("http"):
                continue
            out.append(hit)
    return out
