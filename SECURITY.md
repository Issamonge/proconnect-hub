# Security

## Secrets
- Never commit .env or credentials.
- Database password only in .env (gitignored).

## Data handling
- buyer_signals: public posts only; NO private contact columns by design.
- opt_in_leads: contact data allowed only with consent=true + privacy_accepted=true.
- Outreach: draft-only until human approval; MX + junk checks before any email.
- Bounce rate limit: 3%. On breach, halt campaigns.

## Access
- API is read-only for leads/matches; approval endpoint requires manual action.
- Nginx serves dashboard + API only; no public DB port.

## Compliance
Per-country notes in config/countries.json (CAN-SPAM, PECR, CASL, Spam Act).
Unsubscribe/do-not-contact respected.
