# Engineering Foundation Standard

## Purpose
This document establishes strict engineering principles for AaramBooks development to prevent hardcoded configuration problems, environment variable conflicts, port collisions, and deployment inconsistencies previously observed in Aaram systems (Inventory, Packer, Identity).

---

## 1. Configuration Management Standard
Configuration dictates how the service operates in different environments.
- **No hardcoded URLs:** External service endpoints, databases, and internal network addresses must never be hardcoded in source files.
- **No hardcoded ports:** Application binding ports must be configurable.
- **No hardcoded credentials:** API keys, passwords, and tokens must be loaded securely at runtime.
- **Environment-based configuration:** All environment-specific variables must be injected at runtime via environment variables or a secure vault.
- **.env.example requirements:** Every repository/module must contain a `.env.example` file explicitly listing all required environment variables with safe placeholder values.
- **Development/staging/production separation:** Configurations must cleanly separate environments without requiring code changes to switch contexts.

---

## 2. Port Management Standard
To prevent port collisions on host networks and developer machines:
- **Central port registry:** All service ports must be documented and registered in a centralized architectural document.
- **Service naming convention:** Services must be uniquely and consistently named across environments (e.g., `aarambooks-brain-api`).
- **Port allocation rules:** Port ranges must be logically assigned (e.g., 8000-8099 for core services, 8100-8199 for adapters).
- **Prevention of service conflicts:** New services must verify port availability before defining their default bindings.

### Port Registry

Existing Aaram system reservations:

**AaramPacking:**
- Backend 8001
- Frontend 8002
- Admin Frontend 8003

**AaramInventory:**
- Backend 8100
- Frontend 5173

**AaramIdentity:**
- Backend 9000
- Frontend 9001

**AaramBooks Brain (Reserved):**
- Range 8000-8099
- Brain API initial port 8000

**Rules:**
- No service may select ports outside the registry without approval.
- Database ports should remain internal Docker network ports unless explicitly required.
- Future services must reserve ports before implementation.

---

## 3. Docker Standards
Containerization ensures environment consistency.
- **docker-compose conventions:** The base `docker-compose.yml` should define the generic production-like topology. 
- **development overrides:** Use `docker-compose.override.yml` for local development configurations (e.g., volume mounts, debug ports).
- **service naming rules:** Docker Compose service names must be short, lowercase, and representative of the module (e.g., `brain_core_api`, `pgvector_db`).
- **container naming rules:** Container names must follow the `[project]-[module]-[environment]` format to prevent conflicts (e.g., `aarambooks-brain-core-dev`).

---

## 4. Database Isolation Standards
Data ownership and state isolation rules.
- **Database naming conventions:** Databases must reflect their domain ownership (e.g., `aarambooks_brain_core_dev`).
- **User/schema separation:** Different domains interacting with the same physical cluster must use isolated schemas and strict user permissions.
- **Migration ownership:** Schema migrations (e.g., Alembic, Flyway) are strictly owned by the module that owns the data.
- **Backup considerations:** Vector embeddings and relational session states must have documented backup frequencies based on their business criticality.

---

## 5. Service Configuration Standards
- **Environment variables:** Use a configuration validation library (e.g., Pydantic Settings for Python) to ensure the service crashes immediately on startup if a required environment variable is missing or mistyped.
- **Secrets handling:** Secrets must not be committed to version control. In production, secrets must be injected via a secure secrets manager.
- **External service configuration:** Configurations for ShopDeck, AaramIdentity, and LLM Providers must be distinctly separated in the configuration map.
- **Logging configuration:** Standardized JSON logging must be configured for all services to ensure interoperability with centralized log aggregators.

---

## 6. Service Identity Standard

Every AaramBooks service must have:
- Unique service name
- Unique container name
- Unique database/schema identity
- Unique health endpoint identity
- Documented owning module

Enforce naming that prevents ambiguity across the Aaram ecosystem.

Avoid generic names:
- api
- backend
- server
- service

Prefer explicit names:

Examples:
- aarambooks-brain-api
- aaraminventory-api
- aarampacking-api
- aaramidentity-api

Purpose:
Prevent service conflicts, deployment confusion, and ownership ambiguity across multiple Aaram systems.

---

## 7. Environment Isolation Standard

Define separate environments:
- Development
- Testing / CI
- Staging
- Production

For each environment define:
- Separate database
- Separate credentials
- Separate configuration
- Separate data ownership

Database naming convention:
`{project}_{module}_{environment}`

Examples:
- aarambooks_brain_core_dev
- aarambooks_brain_core_test
- aarambooks_brain_core_staging
- aarambooks_brain_core_prod

Rules:
- Never share databases between environments.
- Never commit environment secrets.
- `.env.example` is the only committed template.
- Production secrets must come from deployment secret management.

### Environment Promotion Rule

Rules:
- Code moves between environments.
- Data does not move automatically between environments.
- Development data must never be promoted to staging or production.
- Production data must never be copied into lower environments without approved sanitization and privacy controls.
- Test data must remain isolated from operational data.

Purpose:
Prevent accidental exposure of customer, order, inventory, operational, or intelligence data across environments.

---

## 8. Deployment Readiness Checklist
Before any service or module is deployed to a shared environment:
- [ ] Configuration reviewed (No hardcoded values detected).
- [ ] Ports registered in the central architecture registry.
- [ ] Environment variables documented in `.env.example`.
- [ ] Database migrations verified and tested in a clean environment.
- [ ] Health checks added (`/health` or `/ready` endpoints returning valid statuses).
- [ ] Service Identity Standard applied (no generic naming).
