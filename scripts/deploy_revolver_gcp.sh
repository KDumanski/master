#!/usr/bin/env bash
# Deploy the Revolver sweep to the GCP box (104.36.87.170) and run it on cron
# every 30 minutes. Re-running this is safe: it just refreshes the code.
#
#   bash scripts/deploy_revolver_gcp.sh
#
# Layout on the server follows the existing /root/<project>/venv convention:
#   /root/revolver/revolver_stories.py   the sweep
#   /root/revolver/google_auth.py        shared Google OAuth helper
#   /root/revolver/.secrets/             Drive token + OAuth client (chmod 600)
#   /root/revolver/revolver.log          rolling run log
#
# The Anthropic key is read from /root/etls/.env, which already has one.
set -euo pipefail

SERVER="${REVOLVER_SERVER:-root@104.36.87.170}"
REMOTE=/root/revolver
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "==> Creating $REMOTE on $SERVER"
ssh "$SERVER" "mkdir -p $REMOTE/.secrets && chmod 700 $REMOTE/.secrets"

echo "==> Copying code"
scp -q "$HERE/revolver_stories.py" "$HERE/revolver_sources.json" \
       "$HERE/google_auth.py" "$SERVER:$REMOTE/"

echo "==> Copying Google credentials (personal Drive token + OAuth client)"
scp -q "$HERE/../.secrets/personal_drive_token.json" \
       "$HERE/../.secrets/credentials.json" "$SERVER:$REMOTE/.secrets/"
ssh "$SERVER" "chmod 600 $REMOTE/.secrets/*"

echo "==> Building venv + installing dependencies"
ssh "$SERVER" "cd $REMOTE && python3 -m venv venv 2>/dev/null || true; \
  ./venv/bin/pip -q install --upgrade pip >/dev/null && \
  ./venv/bin/pip -q install feedparser requests anthropic \
    google-auth google-auth-oauthlib google-api-python-client >/dev/null && \
  echo '    dependencies installed'"

echo "==> Installing cron entry (every 30 minutes)"
# Replace any previous revolver line, keep every other cron job untouched.
ssh "$SERVER" "( crontab -l 2>/dev/null | grep -v 'revolver_stories.py' ; \
  echo '*/30 * * * * cd $REMOTE && ./venv/bin/python revolver_stories.py >> $REMOTE/revolver.log 2>&1' \
  ) | crontab -"

echo "==> Verifying"
ssh "$SERVER" "crontab -l | grep revolver_stories.py"
echo "Deployed. Watch it with:"
echo "  ssh $SERVER 'tail -f $REMOTE/revolver.log'"
