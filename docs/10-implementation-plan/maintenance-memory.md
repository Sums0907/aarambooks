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
