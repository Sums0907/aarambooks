#!/bin/bash
set -e

# Mirrors Aaram_Inventory's mac_to_vps_deploy.sh structure exactly (read directly from
# /Users/sumatidhingra/Documents/AaramBooks/Aaram_Inventory/mac_to_vps_deploy.sh to copy this
# pattern, not guessed) - GitHub Actions builds and pushes the image to GHCR
# (.github/workflows/docker-publish.yml), the VPS only ever pulls it. No `git pull`, no
# `--build`, no source checkout on the VPS at all - Brain's docker-compose.prod.yml has no
# `build:` for this exact reason.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

section() { printf "\n${BOLD}${CYAN}════════════════════════════════════════════════════════${NC}\n${BOLD}${CYAN}  %s${NC}\n${BOLD}${CYAN}════════════════════════════════════════════════════════${NC}\n" "$1"; }
step()    { printf "\n${BOLD}▶ %s${NC}\n" "$1"; }
ok()      { printf "${GREEN}✅ %s${NC}\n" "$1"; }
warn()    { printf "${YELLOW}⚠️  %s${NC}\n" "$1"; }
fail()    { printf "${RED}❌ %s${NC}\n" "$1" >&2; }
info()    { printf "${DIM}   %s${NC}\n" "$1"; }

trap 'fail "Deployment failed at line $LINENO — stopped there, nothing after it ran."' ERR

# Brain lives on the VPS at ~/aarambooks/brain/ - a small directory holding only
# docker-compose.prod.yml, .env, and litellm_config.prod.yaml, matching the sibling
# convention (~/aarambooks/identity, ~/aarambooks/inventory, ~/aarambooks/packing,
# ~/aarambooks/business_systems/shopdeck) - never a full source checkout.
APP_FOLDER="brain"
VPS_USER="aaramhomes"
VPS_IP="200.234.39.72"

section "Starting Full Deployment Pipeline — Brain"

step "[1/3] Committing and pushing code to GitHub"
if [ -n "$1" ]; then
    COMMIT_MSG="$1"
    info "Commit message: $COMMIT_MSG"
else
    read -p "Enter commit message: " COMMIT_MSG
fi
git add .
git commit -m "$COMMIT_MSG" || warn "No new changes to commit."
git push origin main || warn "No new changes to push."

info "GitHub Actions is now building your Docker image in the cloud."
info "🕒 Giving GitHub a few seconds to trigger the Action..."
sleep 5

section "Tracking Live Build Progress"
RUN_ID=$(gh run list --workflow=docker-publish.yml --limit 1 --json databaseId -q ".[0].databaseId")

if [ -z "$RUN_ID" ]; then
    warn "Could not automatically detect the GitHub Action."
    read -p "Please wait a few minutes, then press Enter to trigger the VPS pull... "
else
    if gh run watch $RUN_ID --exit-status; then
        ok "GitHub Action completed successfully!"
    else
        fail "GitHub Action failed — the VPS will NOT be touched."
        exit 1
    fi
fi

step "[3/3] Connecting to VPS to pull and restart"
ssh $VPS_USER@$VPS_IP << EOF
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    BOLD='\033[1m'
    NC='\033[0m'
    trap 'printf "\${RED}❌ VPS deploy failed at line \$LINENO — stopped there, nothing after it ran.\${NC}\n" >&2' ERR
    set -e
    cd ~/aarambooks/$APP_FOLDER

    printf "\${BOLD}Pulling latest images...\${NC}\n"
    docker compose -f docker-compose.prod.yml pull

    printf "\${BOLD}Restarting containers...\${NC}\n"
    docker compose -f docker-compose.prod.yml up -d

    printf "\${BOLD}Running Alembic migrations...\${NC}\n"
    docker exec aarambooks-brain-api alembic upgrade head || true

    printf "\${BOLD}Cleaning up...\${NC}\n"
    docker image prune -f

    printf "\n\${BOLD}Verifying containers actually restarted just now:\${NC}\n"
    docker compose -f docker-compose.prod.yml ps --format '{{.Name}}\t{{.RunningFor}}'

    printf "\${GREEN}✅ VPS Deployment Complete!\${NC}\n"
EOF

section "All Done! Brain is live."
echo ""
echo "Before real customers touch this, confirm:"
echo "  - api-brain.aarambooks.cloud (or chosen domain) is wired to this VPS with TLS,"
echo "    and Exotel's + Sarvam's webhooks point at it"
echo "  - a real, non-mocked smoke test has been run (see docs/claude/ deployment strategy)"
