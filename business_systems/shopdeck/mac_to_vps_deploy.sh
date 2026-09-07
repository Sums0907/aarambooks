#!/bin/bash
set -e

# Change this to whichever app you are deploying (packing, inventory, identity, business_systems/shopdeck)
APP_FOLDER="business_systems/shopdeck"
VPS_USER="aaramhomes"
VPS_IP="200.234.39.72"

echo "========================================="
echo " Starting ShopDeck BS Full Deployment Pipeline"
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

echo "GitHub Actions is now building your Docker image in the cloud."
echo ""
echo "🕒 Giving GitHub a few seconds to trigger the Action..."
sleep 5

echo "=============================================="
echo " Tracking Live Build Progress "
echo "=============================================="
# Fetch the ID of the latest workflow run
RUN_ID=$(gh run list --limit 1 --json databaseId -q ".[0].databaseId")

if [ -z "$RUN_ID" ]; then
    echo "⚠️ Could not automatically detect the GitHub Action."
    read -p "Please wait 3 minutes, then press Enter to trigger the VPS pull... "
else
    # Watch the run and fail the script if the build fails
    gh run watch $RUN_ID --exit-status
    echo "✅ GitHub Action completed successfully!"
fi
# Step 3: Trigger VPS Update
echo ""
echo "[3/3] Connecting to VPS to pull and restart..."
# This sends the deployment commands directly to your VPS over SSH!
ssh $VPS_USER@$VPS_IP << EOF
    echo "Updating VPS source code from GitHub..."
    cd ~/aarambooks
    git pull origin main

    cd ~/aarambooks/$APP_FOLDER
    
    echo "Pulling latest images..."
    docker compose -f docker-compose.prod.yml pull
    
    echo "Restarting containers..."
    docker compose -f docker-compose.prod.yml up -d --build
    
    # Run migrations if it's the backend
    BACKEND_CONTAINER=\$(docker compose -f docker-compose.prod.yml ps -q | xargs -r docker inspect -f '{{.Name}}' | grep "backend" | sed 's/^\///' || true)
    if [ -n "\$BACKEND_CONTAINER" ]; then
        echo "Running Alembic migrations..."
        docker exec "\$BACKEND_CONTAINER" alembic upgrade head || true
        # If ShopDeck uses custom raw SQL migrations, they should be applied here.
        # e.g., docker exec "\$BACKEND_CONTAINER" psql -U postgres -d postgres -f /app/db/migrations/002_ndr_queue_hardening.sql || true
    fi
    
    echo "Cleaning up..."
    docker image prune -f
    
    echo "✅ Shopdeck VPS Deployment Complete!"
EOF

echo ""
echo "========================================="
echo " All Done! Your app - Shopdeck is live."
echo "========================================="
