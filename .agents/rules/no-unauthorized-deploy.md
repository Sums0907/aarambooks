---
description: Absolute prohibition against deploying to the VPS without explicit user permission.
---

# STRICT VPS DEPLOYMENT AUTHORIZATION

**NEVER DEPLOY TO THE VPS WITHOUT EXPLICIT PERMISSION.**

1. **Absolute Block**: You are strictly forbidden from running any deployment scripts (e.g., `mac_to_vps_deploy.sh`), pushing Docker images to production, or restarting VPS services unless the user has explicitly commanded you to do so in the current turn.
2. **Ecosystem Safety**: While a single app's unit tests might pass locally, deploying it can silently break integration points with other apps in the ecosystem (e.g., Identity, ShopDeck, Inventory, Brain).
3. **Mandatory Handoff**: If your current task involves preparing a deployment, you must stop at the preparation phase, outline the deployment command you *would* run, and ask the user to either run it themselves or explicitly authorize you to run it.

Do not make assumptions. "Fix this bug" does not mean "Fix this bug and deploy to production." You must seek separate, explicit authorization for the deployment step.
