---
description: Constraints for ShopDeck VPS Production Deployments
---

# VPS Deployment Constraints

1. **No Manual VPS Modifications**: Never manually connect to the VPS via SSH to deploy code, alter the deployed environment directly, or manually edit configuration files on the production server.
2. **Exclusive Use of Deployment Script**: All production updates for ShopDeck must be deployed exclusively by running the `./mac_to_vps_deploy.sh` script locally from the `business_systems/shopdeck` directory.
3. **Execution Context**: The script handles code pushing, triggering GitHub Actions for CI, and automatically connecting to the VPS to pull and restart the docker containers. Let the script manage the full end-to-end deployment lifecycle.
