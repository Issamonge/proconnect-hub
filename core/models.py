"""Unified lead/business records with required fields and validation. Also migration helpers."""
import json
import os
import uuid
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

LEAD_TYPES = ("intent_signal", "opt_in_lead", "partner_referral",
              "business_candidate", "verified_business")

LEAD_REQUIRED = ["id", "lead_type", "source_platform", "niche", "country",
                 "normalized_location", "summary", "consent_status", "status",
                 "freshness_score", "quality_score", "created_at", "last_verified_at"]

BIZ_REQUIRED = ["id", "name", "niche", "country", "official_website",
                "verification_status", "do_not_contact", "created_at"]

CONSENT = ("no_consent", "opt_in_consent", "referral_consent")
LEAD_STATUS = ("new", "matched", "needs_review", "contacted", "paid", "archived")


def new_lead(**kw):
    if not kw.get("normalized_location") and kw.get("country"):
        kw["normalized_location"] = kw["country"].get("normalized")
    rec = {
        "id": str(uuid.uuid4()),
        "lead_type": kw.get("lead_type", "intent_signal"),
        "source_platform": kw.get("source_platform", "unknown"),
        "source_url": kw.get("source_url", ""),
        "source_post_date": kw.get("source_post_date"),
        "country": kw.get("country", {}),
        "region": kw.get("region"),
        "city": kw.get("city"),
        "normalized_location": kw.get("normalized_location"),
        "latitude": kw.get("latitude", kw.get("country", {}).get("lat")),
        "longitude": kw.get("longitude", kw.get("country", {}).get("lon")),
        "niche": kw.get("niche", ""),
        "requested_service": kw.get("requested_service", ""),
        "urgency": kw.get("urgency", "normal"),
        "language": kw.get("language", "en"),
        "summary": kw.get("summary", ""),
        "title": kw.get("title", ""),
        "consent_status": kw.get("consent_status", "no_consent"),
        "contact_permission": kw.get("contact_permission", False),
        "contact_details": kw.get("contact_details", None),
        "evidence": kw.get("evidence", kw.get("source_url", "")),
        "freshness_score": kw.get("freshness_score", 0),
        "quality_score": kw.get("quality_score", 0),
        "status": kw.get("status", "new"),
        "matched_business_ids": kw.get("matched_business_ids", []),
        "created_at": kw.get("created_at") or _now(),
        "last_verified_at": kw.get("last_verified_at") or _now(),
    }
    missing = [f for f in LEAD_REQUIRED if rec.get(f) in (None, "") and f not in
               ("region", "city", "latitude", "longitude", "source_url", "title",
                "normalized_location")]
    if missing:
        raise ValueError(f"lead missing: {missing}")
    if not rec["normalized_location"] or not rec["country"].get("country_code"):
        rec["status"] = "needs_review"
    return rec


def new_business(**kw):
    rec = {
        "id": str(uuid.uuid4()),
        "name": kw.get("name", ""),
        "niche": kw.get("niche", ""),
        "country": kw.get("country", {}),
        "region": kw.get("region"),
        "city": kw.get("city"),
        "normalized_location": kw.get("normalized_location"),
        "service_radius_km": kw.get("service_radius_km"),
        "address": kw.get("address", ""),
        "phone": kw.get("phone", ""),
        "official_website": kw.get("official_website", ""),
        "public_business_email": kw.get("public_business_email"),
        "source_urls": kw.get("source_urls", []),
        "verification_status": kw.get("verification_status", "unverified"),
        "email_verification_status": kw.get("email_verification_status"),
        "contact_preference": kw.get("contact_preference", "form"),
        "language": kw.get("language", "en"),
        "last_verified_at": kw.get("last_verified_at") or _now(),
        "do_not_contact": kw.get("do_not_contact", False),
        "notes": kw.get("notes", ""),
        "created_at": kw.get("created_at") or _now(),
    }
    return rec


def _now():
    return datetime.now(timezone.utc).isoformat()


def _fname(records):
    return [r["id"] for r in records]


def migrate_leads():
    """Convert old buyer_leads.json into unified records (best-effort, review-safe)."""
    from core.location import normalize_location
    src = os.path.join(DATA, "buyer_leads.json")
    if not os.path.exists(src):
        return []
    old = json.load(open(src))
    out = []
    for l in old:
        loc = normalize_location(l.get("location", ""))
        if loc.get("confidence") == "none":
            status = "needs_review"
        else:
            status = "new"
        try:
            rec = new_lead(
                lead_type="intent_signal",
                source_platform="reddit" if "reddit.com" in l.get("url", "") else "unknown",
                source_url=l.get("url", ""),
                country=loc,
                title=l.get("title", ""),
                niche=l.get("niche") or ("real_estate" if l.get("type") == "renter" else ""),
                summary=l.get("description", ""),
                consent_status="no_consent",
                status=status,
                created_at=l.get("found_at"),
                last_verified_at=_now(),
            )
            rec["matched_business_ids"] = []
            out.append(rec)
        except ValueError:
            continue
    json.dump(out, open(os.path.join(DATA, "leads.json"), "w"), indent=2)
    return out


def migrate_businesses():
    """Convert old scan_results.json into unified business records. Marks unverified."""
    from core.location import normalize_location
    src = os.path.join(DATA, "scan_results.json")
    if not os.path.exists(src):
        return []
    old = json.load(open(src))
    out = []
    for b in old:
        loc = normalize_location(b.get("location", ""))
        rec = new_business(
            name=b.get("name", ""),
            niche=b.get("niche", ""),
            country=loc,
            address=b.get("address", ""),
            phone=b.get("phone", ""),
            official_website=b.get("website", ""),
            source_urls=[b.get("website", "")] if b.get("website") else [],
            verification_status="unverified",
            language=loc.get("language") or "en",
        )
        out.append(rec)
    json.dump(out, open(os.path.join(DATA, "businesses.json"), "w"), indent=2)
    return out
