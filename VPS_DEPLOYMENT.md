# VPS Deployment Guide (Contabo)

Prereqs: SSH access to the VPS.

## 1. Install (once)
```bash
curl -fsSL https://raw.githubusercontent.com/Issamonge/proconnect-hub/master/scripts/install_vps.sh | bash
```

## 2. Configure
```bash
cd proconnect-hub
nano .env     # set DB_PASSWORD; keep DRY_RUN=true OUTREACH_ENABLED=false
```

## 3. Start
```bash
bash scripts/start.sh
```

## 4. Verify
```bash
bash scripts/healthcheck.sh
# open http://<vps-ip>/ and /api/metrics
```

## Daily ops
- Update: `bash scripts/update.sh`
- Backup: `bash scripts/backup_db.sh`
- Stop: `bash scripts/stop.sh`

## Safety defaults
DRY_RUN=true, OUTREACH_ENABLED=false, AUTO_REPLY_ENABLED=false.
Only after reviewing a dry-run do you change these in .env.
