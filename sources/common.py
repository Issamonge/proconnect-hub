"""Shared HTTP / parsing helpers for source adapters."""
import html
import re
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

DDG_DIRECTORY_DENY = ["angi.com", "yelp", "yellowpages", "thumbtack", "homeadvisor",
                      "nextdoor", "reddit.com/r/", "wikipedia", "porch.com", "houzz"]


def html_unescape(s):
    return html.unescape(s)


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def http_get(url, params=None, timeout=15):
    r = requests.get(url, params=params, headers=UA, timeout=timeout)
    if r.status_code != 200:
        return r.status_code, ""
    return 200, r.text


def ddg(query, limit=12):
    """DuckDuckGo html results. Returns list of {title, url, snippet}."""
    status, text = http_get("https://html.duckduckgo.com/html/", params={"q": query})
    if status != 200:
        return []
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', text)
    links = re.findall(r'class="result__a"[^>]*href="(.*?)"', text)
    snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', text, re.DOTALL)
    from urllib.parse import urlparse, parse_qs
    out = []
    for t, l, s in zip(titles, links, snips):
        url = html.unescape(l)
        if "uddg=" in url:
            url = parse_qs(urlparse("https:" + url if url.startswith("//") else url).query).get("uddg", [url])[0]
        out.append({"title": clean(t), "url": url, "snippet": clean(s)})
    return out[:limit]


def as_intent(source_platform, niche, title, url, summary, location_hint=""):
    """Build a minimal intent payload; caller adds the unified record via models."""
    return {
        "source_platform": source_platform,
        "niche": niche,
        "title": title or "",
        "url": url or "",
        "summary": summary or "",
        "location_hint": location_hint or "",
    }
