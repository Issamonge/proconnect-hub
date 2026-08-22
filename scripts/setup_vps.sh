#!/bin/bash
# ============================================================
# VPS SETUP — run ONCE on your Contabo VPS to install everything
# Usage:  bash scripts/setup_vps.sh
# After setup, the system runs every day by itself (cron).
# ============================================================
set -x
cd "$(dirname "$0")/.." || exit 1
REPO_DIR=$(pwd)

# 1. system packages
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git curl

# 2. python env
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install playwright dnspython requests python-dotenv
python3 -m playwright install chromium --with-deps

# 3. .env — created only if missing (you add your password once)
if [ ! -f .env ]; then
  cat > .env <<'EOF'
GMAIL_USER=ihakizimana11@gmail.com
GMAIL_APP_PASSWORD=PUT_YOUR_16_LETTER_APP_PASSWORD_HERE
BUSINESS_EMAIL=ihakizimana11@gmail.com
EOF
  echo ">>> EDIT .env and put your Gmail app password: nano .env"
fi
chmod 600 .env

# 4. initial data build (only if no data yet)
if [ ! -f data/scan_results.json ]; then
  python3 scripts/rebuild_businesses.py
fi

# 5. cron: run daily engine every morning at 07:00 + auto-replyer every 10 min
( crontab -l 2>/dev/null | grep -v daily_engine | grep -v auto_replyer ; \
  echo "0 7 * * * cd $REPO_DIR && $REPO_DIR/.venv/bin/python3 scripts/daily_engine.py >> $REPO_DIR/data/daily_engine.log 2>&1" ; \
  echo "*/10 * * * * cd $REPO_DIR && $REPO_DIR/.venv/bin/python3 scripts/auto_replyer.py --once >> $REPO_DIR/data/auto_replyer.log 2>&1" \
) | crontab -

echo "==================================================="
echo " SETUP DONE!"
echo " - Every day 07:00: daily engine finds buyers+businesses and contacts them"
echo " - Every 10 min: auto-replyer checks Gmail and responds"
echo " - Reports: data/reports/"
echo " - Check anytime: python3 scripts/daily_engine.py --report"
echo "==================================================="
crontab -l
