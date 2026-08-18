#!/bin/bash
# Deploy updated dashboard to Vercel permanently
# Usage: bash scripts/deploy_vercel.sh

cd /workspace/project

VERCEL_TOKEN="${VERCEL_TOKEN:-$(grep VERCEL_TOKEN .env 2>/dev/null | cut -d'=' -f2)}"

echo "=== Regenerating dashboard with latest data ==="
python3 scripts/dashboard.py 2>&1 | tail -2

echo ""
echo "=== Copying to deploy folder ==="
cp dashboard/index.html public/deploy/index.html
cp public/landing.html public/landing_deploy/index.html

echo ""
echo "=== Deploying dashboard to Vercel ==="
npx --yes vercel deploy public/deploy --prod --token $VERCEL_TOKEN --yes 2>&1 | grep -E "Production|Aliased|Ready"

echo ""
echo "=== Deploying landing page to Vercel ==="
npx --yes vercel deploy public/landing_deploy --prod --token $VERCEL_TOKEN --yes 2>&1 | grep -E "Production|Aliased|Ready"

echo ""
echo "=== DONE! ==="
echo "Dashboard: https://deploy-nine-kappa-58.vercel.app"
echo "Landing:   https://landingdeploy-ruddy.vercel.app"
