# AaramBooks Maintenance Memory

LIVING DOCUMENT — PERMANENT AMENDMENT MODE

AG MUST treat this document as permanent repository-level maintenance memory. 
Before maintenance or modification of existing AaramBooks functionality, AG MUST consult it. 
When AG discovers new maintenance-relevant knowledge, AG MUST amend it immediately in the same task. 
This instruction remains active indefinitely and survives completion of the current implementation roadmap.
This document is intentionally never frozen.

==================================================
1. Purpose & Scope
==================================================
This document is the long-term operational memory of AaramBooks. 
Its purpose is to preserve knowledge that a future maintainer would otherwise have to rediscover through trial and error (e.g., quirks, previous failures, deployment constraints, safe/unsafe changes).

**Document Boundary:**
- Architecture / system principles → Architecture documentation / ADRs
- Technical architectural decisions → TDRs
- Current implementation progress → `engineering-log.md`
- Frozen implementation roadmap → `implementation-backlog.md`
- Permanent operational and maintenance knowledge → `maintenance-memory.md`

*Rule:* A maintenance-memory entry must NOT silently override an ADR, TDR, architecture document, or frozen implementation roadmap. If a discovered fact actually requires an architectural or technical decision, AG must flag that and update the appropriate authoritative document through the proper process rather than hiding the decision inside maintenance memory.

==================================================
2. Permanent AG Maintenance Instructions
==================================================
1. **Read** `maintenance-memory.md` before modifying an existing subsystem.
2. **Search** it for relevant component names, integrations, dependencies, known issues, and warnings before maintenance work.
3. **Immediately amend** it when new maintenance knowledge is discovered. Do NOT wait for the user to request an update.
4. **Do not create duplicate entries** when an existing entry can be amended.
5. **Preserve historical knowledge** unless it is demonstrably obsolete.
6. **When knowledge becomes obsolete**, mark it obsolete rather than silently deleting it, unless there is a clear reason deletion is necessary.
7. **If a workaround becomes permanent**, update its classification.
8. **If a recurring failure is discovered**, record the symptoms, cause, detection method, and recovery procedure.
9. **If an external service behaves differently** from its apparent/documented behaviour, record the observed behaviour and evidence.
10. **If a future maintainer could waste significant time** rediscovering something, it belongs here.
11. **Do not use this document as a dumping ground** for ordinary implementation progress.
12. **Do not use this document to bypass** ADR/TDR governance.
13. **Do not silently convert assumptions into facts**. Clearly distinguish: observed, verified, inferred, temporary assumption.
14. **When a maintenance discovery indicates that architecture or an existing decision may be wrong**, flag it for formal review rather than silently changing the architecture.
15. **Never use blanket `git add src/ tests/ docs/` during phase implementation.** Phase commits must explicitly stage ONLY the exact files permitted by the frozen phase boundary to prevent bleeding pre-existing or parallel work into the wrong phase.
16. **Environment Constraint (Coverage):** `pytest-cov` is unavailable in the current locked environment. Attempting package installation may fail because external package sources are inaccessible. Coverage therefore may need to be measured in an environment where the dependency is already provisioned. This is an environment constraint, not an application defect.

==================================================
3. How to Use This Document
==================================================
**"DO NOT MAKE ME REDISCOVER THIS" TEST:**
Before completing any implementation, debugging, deployment, integration, or maintenance task, AG should ask:
*"Did I learn anything during this task that would save a future maintainer significant time, prevent a recurring mistake, prevent an unsafe change, or explain an otherwise surprising behaviour?"*
If YES: → immediately amend `maintenance-memory.md`.
If NO: → no amendment is required.

**Entry Format (Use where applicable):**
- **Date:** 
- **Subsystem / Component:** 
- **Category:** 
- **Observation:** 
- **Why it matters:** 
- **Symptoms:** 
- **Root cause:** 
- **Correct behaviour:** 
- **Recommended action:** 
- **Recovery / workaround:** 
- **Permanent or temporary:** 
- **Related files:** 
- **Related external system:** 
- **Related ADR/TDR if applicable:** 
- **Source / evidence:** 
- **Added or amended by:** 

==================================================
4. Known Operational Constraints
==================================================
- **Aaram-Owned Abstractions:** Must remain provider-independent. Do not leak vendor-specific SDKs into Brain Core contracts.
- **Business System Boundaries:** Brain Core must NOT become the owner of operational truth. AaramInventory and AaramPacking remain the authoritative source of fulfillment truth.

==================================================
5. Known Issues & Failure Modes
==================================================
*(No entries yet)*

==================================================
6. Integration Quirks & External-System Behaviour
==================================================
- **Date:** 2026-08-26
- **Subsystem / Component:** ShopDeck Context Adapter
- **Category:** External-System Behaviour
- **Observation:** Interactive MCP OAuth (mobile number + OTP) is a verified limitation from our investigation. It is incompatible with a headless backend server.
- **Why it matters:** Attempting to build an automated background daemon using the MCP will fail at authentication.
- **Recommended action:** The backend integration must use standard ShopDeck REST/gRPC B2B APIs once headless authentication is secured.
- **Permanent or temporary:** Permanent architectural quirk of the MCP.
- **Source / evidence:** Direct investigation of the ShopDeck MCP connected endpoint.
- **Added by:** AG

- **Date:** 2026-08-26
- **Subsystem / Component:** ShopDeck Context Adapter / NDR Intelligence
- **Category:** Integration Quirks
- **Observation:** Missing NDR/delivery-attempt data is a verified limitation of the exposed MCP schema. Whether equivalent data exists behind another ShopDeck API remains unresolved.
- **Why it matters:** NDR Intelligence loops cannot be built solely relying on the ShopDeck MCP as the single source of truth.
- **Recommended action:** A secondary Logistics/Courier adapter will likely be required to source accurate chronological delivery attempts, unless the standard ShopDeck B2B APIs expose this data.
- **Permanent or temporary:** Pending access to headless B2B APIs to confirm if datasets are hidden behind MCP scopes.
- **Added by:** AG

- **Date:** 2026-08-26
- **Subsystem / Component:** AaramPacking & Context Engine Integration
- **Category:** Integration Quirks & Deployment Boundaries
- **Observation:** AaramPacking is strictly an execution-only system. The authoritative state of fulfillment, logistics, and RTO events (`seller_last_status`, `rto_initiated`) is actually aggregated by the ShopDeck MCP/API.
- **Why it matters:** Brain Core must NOT query AaramPacking for Context. Doing so creates duplicate truth boundaries. ShopDeck is the primary Context Provider for orders, fulfillment, and shipments.
- **Recommended action:** Always map Brain Core context models directly to ShopDeck's exhaustive schema, treating AaramPacking solely as an Action Execution target.
- **Permanent or temporary:** Permanent architectural boundary.
- **Added by:** AG

- **Date:** 2026-08-26
- **Subsystem / Component:** Phase 1 Semantic Context Models
- **Category:** Architecture Principle
- **Observation:** External payloads from AaramInventory (e.g. `confidence_score`) and ShopDeck (e.g. `delivery_time`, `rto_initiated`) are highly granular and exhaustive.
- **Why it matters:** Brain Core semantic models must NEVER mirror external payloads. They represent only the abstract semantics that the Reasoning engine requires (e.g. `items_availability: bool`, `fulfillment_status: str`).
- **Recommended action:** Adapters must downcast, logically derive, and filter complex external data into the simplified, frozen Phase 1 Brain schemas. Do not modify Phase 1 schemas to match external APIs.
- **Permanent or temporary:** Permanent architectural principle.
- **Added by:** AG

- **Date:** 2026-08-29
- **Subsystem / Component:** Inventory Intelligence Domain / Azm Accumulation
- **Category:** Architecture Principle
- **Observation:** Azm (Aaram's proprietary intelligence asset) must be organically accumulated during the execution of Intelligence Domains, rather than built as a separate standalone database. 
- **Why it matters:** As the Inventory Intelligence Domain operates, it must write its case lifecycles, structured reasoning, and action outcomes to the Brain Core Memory Framework (`MemoryProvider`). Simultaneously, it must rely on the `AzmProvider` for its domain semantic knowledge. This strict boundary enables the capture of high-quality Input/Output reasoning traces that form the Azm asset for future open-weight model fine-tuning.
- **Recommended action:** Always persist ID orchestrator state and final decisions to the Memory Framework. Never hardcode SOPs in the ID source code; inject them dynamically from the Knowledge Engine to keep the Azm corpus portable.
- **Permanent or temporary:** Permanent architectural principle.
- **Added by:** AG

- **Date:** 2026-08-26
- **Subsystem / Component:** AaramInventory Webhooks
- **Category:** Integration Quirks & Deployment Boundaries
- **Observation:** In `Aaram_Inventory/src/domains/inventory/api/packer_webhook_router.py`, the `handle_packer_event` endpoint (`/internal/webhooks/packer/events`) explicitly lacks any `Depends(get_current_user)` or permission dependencies, relying purely on network trust, whereas `/force-sync` in the same router requires `INVENTORY_CATALOG_VIEW`.
- **Why it matters:** Internal service-to-service event pushes into AaramInventory currently operate without JWT validation. However, read APIs do strictly enforce JWT validation.
- **Recommended action:** Do not assume all AaramInventory endpoints enforce identity. Differentiate between legacy network-trusted webhooks and strict JWT-enforced API routes when planning integrations.
- **Permanent or temporary:** Temporary until Phase 2 Identity (Service Accounts) unifies M2M authentication.
- **Added by:** AG

- **Date:** 2026-08-26
- **Subsystem / Component:** AaramInventory Authentication Dependency
- **Category:** Integration Quirks & Deployment Boundaries
- **Observation:** `AaramInventory`'s `get_current_user` dependency automatically handles non-UUID `sub` claims by wrapping them in a `uuid5` hash.
- **Why it matters:** AaramIdentity Service Accounts can safely inject string-based client IDs (e.g. `brain-core-service`) into the `sub` claim of a JWT without breaking AaramInventory's backend user resolution.
- **Recommended action:** M2M implementations do not need to modify AaramInventory's JWT validation to support service tokens.
- **Permanent or temporary:** Permanent architectural capability.
- **Added by:** AG

- **Date:** 2026-08-26
- **Subsystem / Component:** AaramInventory Auth Boundary
- **Category:** Integration Quirks & Security Distinction
- **Observation:** AaramIdentity authenticates/identifies Brain as a service, but AaramInventory's current inventory balance endpoint does not enforce that authentication/authorization.
- **Why it matters:** Do not confuse successful M2M authentication with endpoint-level authorization. M2M provides identity, but the endpoint is currently public.
- **Recommended action:** Recognize the security distinction and do not falsely claim the balance endpoint is protected by M2M authorization.
- **Permanent or temporary:** Permanent distinction.
- **Added by:** AG

==================================================
7. Deployment & Environment Knowledge
==================================================
- **Infrastructure Procurement:** Commodity infrastructure (Databases, Event Buses, Gateway Routers) is intentionally BUY/USE. Do not assume or require Docker-based self-hosting for these components during deployment if managed SaaS is available.

==================================================
8. Recovery & Troubleshooting Knowledge
==================================================
*(No entries yet)*

==================================================
9. Dependency & Compatibility Knowledge
==================================================
*(No entries yet)*

==================================================
10. Performance & Scaling Knowledge
==================================================
*(No entries yet)*

==================================================
11. Security & Operational Safety Notes
==================================================
*(No entries yet)*

==================================================
12. Testing & Validation Knowledge
==================================================
*(No entries yet)*

==================================================
13. Upgrade / Migration Knowledge
==================================================
*(No entries yet)*

==================================================
14. Things That Must Not Be Changed Casually
==================================================
- **Mature Operational Systems:** AaramInventory and AaramPacking must NOT be casually redesigned or refactored by Brain Core teams. Their data structures should be adapted to the Brain Core context engine, not the other way around.

==================================================
15. Temporary Workarounds
==================================================
*(No entries yet)*

==================================================
16. Historical Maintenance Lessons
==================================================
*(No entries yet)*

==================================================
17. Maintenance Amendment Log
==================================================
- **2026-08-26:** Document created and initialized with known ShopDeck integration quirks and Build-vs-Buy operational constraints by AG.

AG MUST treat this document as permanent repository-level maintenance memory. 
Before maintenance or modification of existing AaramBooks functionality, AG MUST consult it. 
When AG discovers new maintenance-relevant knowledge, AG MUST amend it immediately in the same task. 
This instruction remains active indefinitely and survives completion of the current implementation roadmap.
This document is intentionally never frozen.
