# ShopDeck Master Deployment Runbook

This document serves as the single source of truth for deploying, verifying, and troubleshooting the ShopDeck Business System in production.

## 1. Architectural Overview

ShopDeck operates as a set of Docker containers running on a monolithic production VPS.
Unlike some of the other AaramBooks services (which build Docker images in GitHub Actions and push to GHCR), ShopDeck builds its images **locally on the VPS** using a synchronized checkout of the `aarambooks.git` repository.

### Component Map
*   **Git Repository**: `aarambooks/business_systems/shopdeck`
*   **VPS Path**: `/home/aaramhomes/aarambooks/business_systems/shopdeck`
*   **Containers**:
    *   `shopdeck-api`: The FastAPI backend serving traffic on port `8210` (internal: `8200`).
    *   `shopdeck-sync`: Background sync worker daemon.
    *   `shopdeck-postgres`: PostgreSQL 16 database holding the NDR queue and operational tables.

## 2. Standard Deployment Procedure

**CRITICAL RULE**: Do not manually SSH into the VPS to perform code edits or deployments.

All deployments must be executed from your local macOS environment using the centralized deployment script.

### Step 1: Execute the Deployment Script
Run the script from your local machine, passing in a commit message if you have uncommitted changes:
```bash
cd ~/aarambooks/business_systems/shopdeck
./mac_to_vps_deploy.sh "feat: your commit message"
```

### Step 2: What the Script Does Automatically
1.  **Commits and Pushes**: Commits your local changes and pushes them to `origin/main`.
2.  **Waits for CI**: Monitors the GitHub Actions pipeline (`ci.yml`) to ensure safety checks and tests pass.
3.  **Synchronizes Code**: SSH connects to the VPS, navigates to `~/aarambooks`, and runs `git pull origin main` to synchronize the latest source code.
4.  **Rebuilds Containers**: Triggers a `docker compose up -d --build` inside `~/aarambooks/business_systems/shopdeck` to pull in the fresh source files and rebuild the `shopdeck-api` and `shopdeck-sync` images.
5.  **Applies Migrations**: Automatically runs `alembic upgrade head` inside the running backend container to apply any new database schema changes.

## 3. Database Migrations

### Creating a Migration
If you make changes to the SQLAlchemy models, generate a new migration locally:
```bash
docker exec -it shopdeck-api alembic revision --autogenerate -m "description of changes"
```
Or for pure SQL migrations (following the established convention):
1. Create a new file in the migrations directory (e.g., `002_ndr_queue_hardening.sql`).
2. *Note: Pure SQL migrations currently require manual application or custom steps in the deploy script if not managed by Alembic.* 
**CRITICAL**: Never modify previously applied migrations (e.g., `001_ndr_queue.sql`). Always create a new file `002_*.sql`.

### Applying Migrations
Migrations are applied automatically during `mac_to_vps_deploy.sh`. 
If you need to apply them manually for troubleshooting:
```bash
ssh aaramhomes@200.234.39.72
cd ~/aarambooks/business_systems/shopdeck
docker exec -it shopdeck-api alembic upgrade head
```

## 4. Environment Configuration (`.env`)

The production `.env` file is maintained directly on the VPS at:
`/home/aaramhomes/aarambooks/business_systems/shopdeck/.env`

If you introduce a new environment variable in the codebase:
1. SSH into the VPS.
2. Edit the `.env` file using `nano .env`.
3. Ensure the variable is exposed in `docker-compose.prod.yml` under the `environment:` section of the relevant services.
4. Run `docker compose -f docker-compose.prod.yml up -d` to restart the containers with the new config.

## 5. Verification & Troubleshooting

### Viewing Logs
If the deployment succeeds but the application behaves unexpectedly, check the logs on the VPS:
```bash
ssh aaramhomes@200.234.39.72

# View API Logs
docker logs -f shopdeck-api

# View Sync Worker Logs
docker logs -f shopdeck-sync

# View Database Logs
docker logs -f shopdeck-postgres
```

### Synthetic Verification
To verify the integrity of the NDR queue and the atomic endpoints (`register_engagement_atomic`, `persist_intelligence_atomic`) in production, you can run the synthetic verification script:

```bash
cd ~/aarambooks/business_systems/shopdeck
# If using the sandbox/IDE tools:
python3 scratch/verify_vps.py
```
*Note: Ensure your `verify_vps.py` payload uses a `claimer_id` that matches the subject (`sub`) of the JWT token to pass the Live Guard safety check.*

### Recovering from a Desync
If the VPS `aarambooks` repository gets stuck in a detached head or merge conflict state:
1. SSH into the VPS: `ssh aaramhomes@200.234.39.72`
2. Run the recovery commands:
```bash
cd ~/aarambooks
git fetch origin main
git reset --hard origin/main
git clean -fd
```
*(Warning: `git clean -fd` will remove untracked files. Ensure production `.env` files and other critical untracked infrastructure files are safely stored outside the git directory structure before running this).*
