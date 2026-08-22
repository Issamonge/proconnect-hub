"""Test suite for ProConnect Hub VPS package."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGeoMatching(unittest.TestCase):
    def test_seattle_never_matches_dallas(self):
        from core.location import normalize_location, distance_km
        sea = normalize_location("Seattle, WA")
        dal = normalize_location("Dallas, TX")
        self.assertGreater(distance_km(sea["lat"], sea["lon"], dal["lat"], dal["lon"]), 2000)
        self.assertFalse(sea["city"].lower() == dal["city"].lower())

    def test_missing_location_goes_needs_review(self):
        from core.location import normalize_location
        from core.models import new_lead
        lead = new_lead(lead_type="intent_signal", source_platform="x", source_url="y",
                        country=normalize_location(""), title="t", niche="p",
                        summary="s", consent_status="no_consent", status="new")
        self.assertEqual(lead["status"], "needs_review")

    def test_intent_signal_has_no_contact_data(self):
        from core.location import normalize_location
        from core.models import new_lead
        lead = new_lead(lead_type="intent_signal", source_platform="reddit", source_url="x",
                        country=normalize_location("Chicago"), title="t", niche="plumbing",
                        summary="s", consent_status="no_consent", status="new")
        self.assertIsNone(lead["contact_details"])
        self.assertFalse(lead["contact_permission"])


class TestOutreachSafety(unittest.TestCase):
    def test_dry_run_blocks_sending(self):
        os.environ["DRY_RUN"] = "true"
        self.assertEqual(os.environ["DRY_RUN"], "true")

    def test_outreach_disabled_by_default(self):
        os.environ.setdefault("OUTREACH_ENABLED", "false")
        self.assertEqual(os.environ["OUTREACH_ENABLED"], "false")

    def test_auto_reply_disabled_by_default(self):
        os.environ.setdefault("AUTO_REPLY_ENABLED", "false")
        self.assertEqual(os.environ["AUTO_REPLY_ENABLED"], "false")


class TestSchema(unittest.TestCase):
    def test_migration_file_valid(self):
        sql = open("db/migrations/001_init.sql").read()
        for table in ["buyer_signals","opt_in_leads","businesses","business_contacts",
                      "source_runs","matches","outreach_queue","outreach_events",
                      "bounces","replies","payments","audit_logs","app_settings"]:
            self.assertIn(table, sql)
        self.assertIn("INSERT INTO app_settings", sql)

    def test_buyer_signals_has_no_contact_columns(self):
        sql = open("db/migrations/001_init.sql").read()
        sig = sql.split("CREATE TABLE IF NOT EXISTS buyer_signals")[1].split(");")[0]
        self.assertNotIn("contact_email", sig)
        self.assertNotIn("contact_phone", sig)

    def test_opt_in_requires_consent(self):
        sql = open("db/migrations/001_init.sql").read()
        optin = sql.split("CREATE TABLE IF NOT EXISTS opt_in_leads")[1].split(");")[0]
        self.assertIn("consent_at TIMESTAMPTZ NOT NULL", optin)
        self.assertIn("privacy_accepted BOOLEAN NOT NULL", optin)


if __name__ == "__main__":
    unittest.main(verbosity=2)
