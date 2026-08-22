-- ProConnect Hub initial schema (PostgreSQL)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS buyer_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_platform TEXT NOT NULL,
  source_url TEXT NOT NULL UNIQUE,
  source_post_date TIMESTAMPTZ,
  country_code TEXT, region TEXT, city TEXT,
  normalized_location TEXT, latitude DOUBLE PRECISION, longitude DOUBLE PRECISION,
  niche TEXT NOT NULL, requested_service TEXT, urgency TEXT DEFAULT 'normal',
  language TEXT DEFAULT 'en', title TEXT, summary TEXT,
  freshness_score INT DEFAULT 50, quality_score INT DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'new',
  evidence TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  last_verified_at TIMESTAMPTZ DEFAULT now()
);
-- intent_signal only: public request. NO private contact columns here by design.

CREATE TABLE IF NOT EXISTS opt_in_leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  country_code TEXT, region TEXT, city TEXT, normalized_location TEXT,
  latitude DOUBLE PRECISION, longitude DOUBLE PRECISION,
  niche TEXT NOT NULL, requested_service TEXT, urgency TEXT DEFAULT 'normal',
  language TEXT DEFAULT 'en', summary TEXT,
  contact_name TEXT, contact_email TEXT, contact_phone TEXT, contact_preference TEXT,
  consent_text TEXT NOT NULL, consent_at TIMESTAMPTZ NOT NULL,
  consent_ip INET, consent_user_agent TEXT,
  privacy_accepted BOOLEAN NOT NULL DEFAULT false,
  status TEXT NOT NULL DEFAULT 'new',
  created_at TIMESTAMPTZ DEFAULT now()
);
-- ONLY opt_in_leads may hold contact data, and only after consent.

CREATE TABLE IF NOT EXISTS businesses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL, niche TEXT NOT NULL,
  country_code TEXT, region TEXT, city TEXT, normalized_location TEXT,
  service_radius_km INT, address TEXT,
  phone TEXT, official_website TEXT,
  source_urls TEXT[] DEFAULT '{}',
  verification_status TEXT NOT NULL DEFAULT 'unverified',
  contact_preference TEXT DEFAULT 'form',
  language TEXT DEFAULT 'en',
  do_not_contact BOOLEAN NOT NULL DEFAULT false,
  notes TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT now(),
  last_verified_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (name, city, niche)
);

CREATE TABLE IF NOT EXISTS business_contacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  channel TEXT NOT NULL,
  value TEXT NOT NULL,
  verification_status TEXT NOT NULL DEFAULT 'unverified',
  verified_at TIMESTAMPTZ,
  do_not_contact BOOLEAN NOT NULL DEFAULT false,
  UNIQUE (business_id, channel, value)
);

CREATE TABLE IF NOT EXISTS source_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL, niche TEXT, country_code TEXT,
  started_at TIMESTAMPTZ DEFAULT now(), finished_at TIMESTAMPTZ,
  found INT DEFAULT 0, errors TEXT,
  status TEXT DEFAULT 'running'
);

CREATE TABLE IF NOT EXISTS matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_kind TEXT NOT NULL,
  lead_id UUID NOT NULL,
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  match_score INT NOT NULL, distance_km DOUBLE PRECISION,
  city_lead TEXT, city_business TEXT,
  status TEXT NOT NULL DEFAULT 'proposed',
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (lead_kind, lead_id, business_id)
);

CREATE TABLE IF NOT EXISTS outreach_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  contact_id UUID NOT NULL REFERENCES business_contacts(id) ON DELETE CASCADE,
  channel TEXT NOT NULL DEFAULT 'email',
  subject TEXT, body_preview TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  approved_by TEXT, approved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outreach_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  outreach_id UUID NOT NULL REFERENCES outreach_queue(id) ON DELETE CASCADE,
  event TEXT NOT NULL,
  detail TEXT, at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bounces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL, reason TEXT,
  hard BOOLEAN NOT NULL DEFAULT true,
  at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS replies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  outreach_id UUID REFERENCES outreach_queue(id),
  from_email TEXT, body TEXT, intent TEXT,
  at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id UUID REFERENCES matches(id),
  amount NUMERIC(10,2), currency TEXT, method TEXT,
  status TEXT DEFAULT 'pending',
  at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor TEXT, action TEXT NOT NULL, detail JSONB,
  at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO app_settings (key, value) VALUES
  ('DRY_RUN', 'true'),
  ('OUTREACH_ENABLED', 'false'),
  ('AUTO_REPLY_ENABLED', 'false'),
  ('BOUNCE_RATE_LIMIT', '0.03')
ON CONFLICT (key) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_signals_city ON buyer_signals (country_code, city, niche);
CREATE INDEX IF NOT EXISTS idx_businesses_city ON businesses (country_code, city, niche);
CREATE INDEX IF NOT EXISTS idx_matches_lead ON matches (lead_kind, lead_id);
