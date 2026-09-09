#!/bin/bash
set -e

# Brain lives at the root of this monorepo (unlike business_systems/shopdeck, which is a
# subfolder deployed via its own mac_to_vps_deploy.sh) - so there is no APP_FOLDER cd here,
# every command below runs from ~/aarambooks directly.
VPS_USER="aaramhomes"
VPS_IP="200.234.39.72"

echo "========================================="
echo " Starting Brain Full Deployment Pipeline"
echo "========================================="

# Step 1: Push to GitHub
echo ""
echo "[1/3] Committing and pushing code to GitHub..."
if [ -n "$1" ]; then
    COMMIT_MSG="$1"
    echo "Commit message: $COMMIT_MSG"
else
    read -p "Enter commit message: " COMMIT_MSG
fi
git add . || true
git commit -m "$COMMIT_MSG" || echo "No new changes to commit."
git push origin main || echo "No new changes to push."

echo "GitHub Actions is now validating the production Docker build."
echo ""
echo "🕒 Giving GitHub a few seconds to trigger the Action..."
sleep 5

echo "=============================================="
echo " Tracking Live Build Progress "
echo "=============================================="
RUN_ID=$(gh run list --limit 1 --json databaseId -q ".[0].databaseId")

if [ -z "$RUN_ID" ]; then
    echo "⚠️ Could not automatically detect the GitHub Action."
    read -p "Please wait a few minutes, then press Enter to trigger the VPS pull... "
else
    gh run watch $RUN_ID --exit-status
    echo "✅ GitHub Action completed successfully!"
fi

# Step 3: Trigger VPS Update
echo ""
echo "[3/3] Connecting to VPS to pull and restart..."
ssh $VPS_USER@$VPS_IP << 'EOF'
    cd ~/aarambooks

    echo "Pulling latest source from GitHub..."
    git pull origin main

    echo "Rebuilding and restarting Brain..."
    docker compose -f docker-compose.prod.yml up -d --build

    echo "Waiting for Brain to report healthy..."
    for i in $(seq 1 12); do
        STATUS=$(docker inspect --format='{{.State.Health.Status}}' aarambooks-brain-api 2>/dev/null || echo "starting")
        if [ "$STATUS" = "healthy" ]; then
            echo "✅ Brain is healthy."
            break
        fi
        echo "  ...still $STATUS ($i/12)"
        sleep 5
    done

    echo "Cleaning up..."
    docker image prune -f

    echo "✅ Brain VPS Deployment Complete!"
EOF

echo ""
echo "========================================="
echo " All Done! Brain is live."
echo "========================================="
echo ""
echo "Before real customers touch this, confirm:"
echo "  - api-brain.aarambooks.cloud (or chosen domain) is wired to this VPS with TLS,"
echo "    and Exotel's webhook + EXOTEL_WEBHOOK_BASE_URL point at it"
echo "  - litellm_config.prod.yaml's model routing has been reviewed and approved"
echo "  - a real, non-mocked smoke test has been run (see docs/claude/ deployment strategy)"
