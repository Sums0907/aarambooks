# RABTA Context Execution Module (CEM) Integration Contract

## 1. Executive Summary
This document defines the strict, generic API contract required for any external business service to participate in the AaramBooks RABTA ecosystem as a **Context Execution Module (CEM)**. 

RABTA (the Brain Core) acts as the cognitive orchestration layer. It translates natural user language into structured, semantic evidence requests. 
A **CEM** acts as the physical execution layer. It translates those semantic requests into physical database queries against its own business reality, and returns factual evidence back to Brain Core.

**Golden Rule:** Brain Core does not know your database schema. You do not know Brain Core's conversational reasoning. You are decoupled via this generic JSON API.

## 2. Ecosystem Flow & Ownership

To understand your role as a CEM, you must understand the exact routing, identity, and authorization flow of the ecosystem.

- **Application**
  - Selects the requested Intelligence Domain (`id_urn`).
  - Selects the Context Execution Module (`cem_urn`).
  - Requests Brain Core to orchestrate them.

- **AaramIdentity**
  - Authenticates the Application.
  - Owns authentication, application identity, users, roles, permissions, and tokens.
  - *Explicitly: AaramIdentity does NOT own CEM identity or routing.*

- **Brain Core (RABTA)**
  - Authorizes the application's request to use the requested ID/CEM at the ecosystem level (`application_id` → allowed `id_urns` / `cem_urns`).
  - Resolves the ID and CEM independently using its infrastructure.
  - Sends the pure semantic request to the CEM.
  - *Explicitly: Brain Core does NOT own the CEM or ID, nor does it establish a relationship between them.*

- **CEM (Context Execution Module)**
  - Is an application-owned execution capability with a stable identity (`cem_urn`).
  - Receives the semantic request.
  - Operates against application business reality.
  - *Explicitly: The CEM does NOT select or dictate the Intelligence Domain.*

- **Intelligence Domain (ID)**
  - *Explicitly: The ID does NOT select or dictate the CEM.*

## 3. Your Responsibilities as a CEM (R-4 / R-5 / R-7)
As a CEM, you ultimately provide the execution boundary for three distinct architectural phases. 

1. **R-4 (Business Discovery):** Inspect the abstract semantic request from Brain Core and determine if your business system has the capability/data to fulfill it.
   - *Constraint:* R-4 MUST NOT perform state-changing execution.
2. **R-5 (Entity Resolution):** Translate fuzzy, semantic references (e.g., "blue bedsheets") into your opaque physical identifiers (e.g., UUIDs). Handle spelling mistakes, fuzzy matching, and multiple candidates internally.
   - *Constraint:* R-5 MUST NOT make conversational decisions.
3. **R-7 (Business Execution):** If the request implies a business action (e.g., "create an order") and execution is safe, perform the action against your database.
   - *Constraint:* R-7 exclusively owns state-changing execution.

*Note: R-4 is not architecturally required to invoke R-5. Whether a concrete CEM internally reuses or invokes its R-5 implementation during discovery is an implementation decision, provided the phase boundaries remain observable and responsibilities are not conflated.*

You must **NOT**:
- Try to answer conversational questions (e.g., "Did you mean X or Y?"). Just return the multiple candidates.
- Format text for the user. Return raw data.
- Worry about how the user asked the question. 

## 4. The R-4.0 API Contract
Your CEM must expose an endpoint (or internal adapter interface) that accepts the `AbstractEvidenceRequest` JSON schema and returns the `BusinessEvidenceResponse` JSON schema.

### Input: `AbstractEvidenceRequest`
This payload is purely semantic. It contains the `ClassifiedRequirement` derived from the user's intent. It includes:
- **`intent`:** What the user wants (e.g., `RETRIEVE`, `ACTION`).
- **`entities`:** Semantic strings representing objects (e.g., `original_expression: "SKU123"`).
- **`conditions`:** Semantic filters (e.g., `operator: "GREATER_THAN", value: "50"`).
- **`refinement_context`:** (Optional) If Brain Core is requesting a follow-up refinement pass, instructions will be provided here.

**CRITICAL ROUTING RULE:** Routing identifiers (`id_urn`, `cem_urn`, `application_id`, URLs, service names, physical metadata) MUST remain OUTSIDE `AbstractEvidenceRequest`. The payload remains purely semantic.

### Output: `BusinessEvidenceResponse`
Your API must return a structured factual response containing:
- **`status`:** A `BusinessRealityStatus` enum.
- **`capabilities_discovered`:** A list of capability URNs your system identified as relevant to the request.
- **`resolved_candidates`:** A dictionary mapping the semantic entity references to your opaque physical `CandidateEntity`s.
- **`execution_limitations`:** If you cannot execute because mandatory parameters are missing, list them here.
- **`evidence_data`:** The raw factual JSON data if discovery/execution succeeded.

## 5. Architectural Principles

### 1. Schema Agnosticism
Brain Core knows **nothing** about your SQL tables or API paths. You must map the generic semantic conditions (e.g., `domain.entity.id EQUALS "123"`) to your internal SQL constraints.

### 2. Opaque Identifiers
When you resolve an entity, you return a `business_id` (e.g., a UUID). Brain Core treats this string opaquely. If Brain Core requires a refinement pass, it will hand that exact `business_id` back to you. You do not need to explain the UUID to Brain Core.

### 3. Independent Authorization
While Brain Core enforces ecosystem-level authorization, your CEM receives the authenticated application context (e.g. `application_id`) OUTSIDE of the `AbstractEvidenceRequest` (e.g. via HTTP headers or metadata envelopes). Your CEM MAY independently enforce business/data authorization required to protect its own business reality based on this context. However, your CEM MUST NOT become the ecosystem-level authority for deciding whether an application is allowed to invoke a particular CEM.

### 4. One Bounded Refinement Pass
Execution is not always a single shot. Brain Core may send you a request, to which you reply `MULTIPLE_CANDIDATES`. Brain Core will ask the user to clarify, and then Brain Core will invoke your endpoint *a second time*, passing the user's chosen `business_id` in the `refinement_context`. Your API must be stateless enough to handle this refinement gracefully.

---

## 6. CEM Onboarding Blueprint (Agent Prompt Template)

If you are instructing an AI agent to build the R-4 (Business Discovery) phase in your specific CEM workspace, you can copy and paste the following strict prompt template to ensure architectural compliance.

***

**RABTA R-4 — BUSINESS DISCOVERY**
**DESIGN AUDIT ONLY — DO NOT IMPLEMENT YET**

You are now working in the target CEM workspace. 

RABTA Phase R-4.0 (The Generic CEM API Contract) has been formally completed in the Brain Core workspace.

The architectural rule is now frozen:
- R-4.0 = Brain Core responsibility (Defining the generic contract).
- R-4 = Concrete CEM Business Discovery responsibility (Implementing it).

Your job now is ONLY to audit and design the CEM-side implementation of R-4.

**IMPORTANT BOUNDARIES**
Assume the CEM workspace operates as an independent service. It will receive the `AbstractEvidenceRequest` as a JSON payload (e.g., via a REST API endpoint) and return the `BusinessEvidenceResponse` as JSON. 

AaramIdentity owns authentication and application identity. Brain Core handles ecosystem-level authorization. You will receive authenticated application context (e.g., `application_id`) via out-of-band mechanisms (e.g. HTTP headers/metadata), NOT inside the `AbstractEvidenceRequest` JSON payload. You MAY independently enforce business/data authorization based on this context. 

Do NOT attempt to symlink or directly import Brain Core's Python files into the CEM workspace. The CEM must be independently implementable. 

*Note: The mechanism by which the generic CEM contract is represented locally in the CEM workspace (e.g., duplicated models, generated models, versioned SDK, OpenAPI/JSON Schema) is an API-contract/versioning decision and is NOT part of R-4 business discovery. Do not make a final architectural decision about shared Python models versus generated/local models during this phase. Flag that decision separately as an API contract/versioning consideration if necessary.*

**REQUIRED READING**
Read the following public API contract and data structures before doing anything. You MUST NOT assume anything about how the calling system (Brain) works internally. You are building an independent API.
1. `/Users/sumatidhingra/aarambooks/docs/06-api-contracts/RABTA-CEM-INTEGRATION-CONTRACT.md` (Focus ONLY on the R-4/R-5/R-7 responsibilities and contract rules. Treat this as the public integration contract).
2. `/Users/sumatidhingra/aarambooks/src/shared/evidence_request_contracts.py` (Treat the request/response schemas defined here as strict API contract definitions. Treat this as your API specification).

*(Do not look at Brain's orchestrator or interface files. You are completely decoupled from Brain's internal implementation).*

**CEM RESPONSIBILITY**
Design how the CEM will receive `AbstractEvidenceRequest`, perform R-4 (BUSINESS DISCOVERY), and return `BusinessEvidenceResponse`.
R-4 is discovery only.
Do NOT implement R-5 Entity Resolution yet.
Do NOT implement R-7 Execution yet.
Do NOT implement R-6 refinement yet.

**AUDIT THE EXISTING SYSTEM**
Inspect the repository and identify:
1. What component is currently the actual CEM.
2. Existing ContextCapabilityGateway / capability mechanisms.
3. Existing SemanticResolverRegistry or equivalent.
4. Existing repositories/services that can provide business reality.
5. Existing capability definitions.
6. Existing product/entity lookup mechanisms.
7. Existing database/schema access that R-4 may legitimately use.
8. Existing legacy compatibility bridge.
9. Existing tests that constrain the implementation.
10. Any existing logic that should be reused rather than duplicated.

R-4 MUST be implemented against the target application's actual business reality.

**DEFINE R-4 PRECISELY**
Design the CEM's R-4 responsibility as:
Input: `AbstractEvidenceRequest` (Semantic payload ONLY, no routing IDs)
Processing:
- understand which business evidence is being requested
- determine whether the CEM has the relevant capability
- discover relevant business candidates/data
- report factual business reality
- do NOT make conversational decisions
Output: `BusinessEvidenceResponse`

The CEM may know: its database schema, tables, SQL, repositories, capability registry, physical business identifiers, and APIs.
RABTA must know none of these.

R-4 must NOT make the CEM responsible for: deciding what the user meant conversationally, deciding whether the user should be asked a question, broadening conversational intent, or interpreting business evidence for the user. Those remain outside R-4.

**CRITICAL R-4 / R-5 SEPARATION**
Explicitly determine where the boundary lies between:
R-4 (Business Discovery): "Can I find business reality/candidates relevant to this abstract request?"
and
R-5 (Entity Resolution): "Which exact physical entity does this semantic reference correspond to?"
*Constraint:* R-5 MUST NOT make conversational decisions.

Do not accidentally implement fuzzy/entity resolution as part of R-4 unless the existing architecture demonstrates that a minimal discovery step is inseparable from resolution. If that occurs, document the boundary explicitly and STOP for approval.

**CRITICAL R-4 / R-7 SEPARATION**
R-4 must not perform business-changing execution. It may discover whether execution capability exists and report that capability, but actual execution belongs to R-7. R-7 exclusively owns state-changing execution.

**LEGACY BRIDGE**
Audit any current temporary compatibility bridges. Determine what it currently does, what R-4 will replace, what must remain temporarily, what can eventually be deleted, and whether any existing functionality can be safely reused by the new CEM. Do NOT delete the bridge during this audit.

**DELIVERABLE**
Create an R-4 design/audit report documenting:
1. Current CEM architecture
2. Existing reusable components
3. Exact R-4 responsibility
4. R-4 input/output flow
5. R-4 vs R-5 boundary
6. R-4 vs R-7 boundary
7. Required new files
8. Existing files requiring modification
9. Existing files that must remain untouched
10. Legacy bridge migration strategy
11. Test strategy
12. Any architectural blockers
13. Proposed implementation sequence

Do NOT modify Brain Core/RABTA.
Do NOT modify the RABTA master documentation.
Do NOT implement code.

FINAL STATUS MUST BE ONE OF:
`R-4 DESIGN READY FOR IMPLEMENTATION` or `R-4 BLOCKED — ARCHITECTURAL DECISION REQUIRED`
