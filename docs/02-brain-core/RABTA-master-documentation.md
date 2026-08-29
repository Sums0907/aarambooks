# RABTA — Master Architecture & Implementation Documentation

## 1. Executive Summary
RABTA establishes the architectural bridge between the user's natural language and the physical execution of business systems. It moves the Brain Core away from strict, exact-identifier schema requirements and introduces progressive, conversational entity resolution, semantic query broadening, and intelligent clarification. It is the intelligence layer that decouples physical data execution from cognitive reasoning. Rabta introduces ONE BOUNDED REFINEMENT LOOP into the lifecycle, allowing Brain to refine a request based on actual business evidence returned by the Context Execution Module (CEM).

## 2. Why Rabta Exists
The current system successfully tokenizes intent but suffers from exact-matching rigidity. It requires explicit, schema-aligned identifiers (e.g., UUIDs) to execute safely. For instance, the system treats "Give me the stock of SKU KD-MDB-MGLD-SK" differently from "Show me blue bedsheets," blocking execution if rigid identifiers are omitted. Rabta exists to solve this impedance mismatch by adapting the business system to the user's natural language, not the other way around.

## 3. Meaning of the Name "Rabta"
"Rabta" (رابطہ) is an Urdu word meaning connection, relationship, contact, linkage, or a bridge between entities. Architecturally, it signifies the intelligent linkage connecting abstract conversational intent, through Brain reasoning, down to physical business data execution, removing the need for Brain Core to inherently understand physical database schemas.

## 4. Existing Architecture — Baseline
- **Brain Core** orchestrates the semantic requirements and delegates physical resolution to external systems via generic contracts.
- **Context Execution Module (CEM)** acts as the physical capability gateway. It was recently updated to intercept requests and translate semantic identities (strings) into physical system identifiers (UUIDs) via a SemanticResolverRegistry.
- **Intelligence Domains (IID)** act as the understanding boundary, transforming user chat intents into Evidence Requirements via LLM extraction.
- **Baseline Truth**: Physical adapters are removed from Brain Core. The domains handle semantic structure, while business systems (AaramInventory, Azm) retain authoritative truth.

## 5. Current Query Lifecycle
1. User provides natural language input.
2. Intelligence Domain (IID) interprets intent and extracts constrained values (e.g. `inventory.entity.sku = "126BS"`).
3. Brain Core packages these constraints into an `EvidenceRequirement` without understanding the underlying schema.
4. The requirement is sent to CEM via the generic `ContextCapabilityGateway`.
5. CEM receives the semantic constraint, attempts translation via middleware/registry, and executes against the database.
6. The exact output or execution failure is returned to Brain Core for interpretation.

## 6. Existing Capabilities
The system has working intelligence domains (like Inventory Intelligence Domain) and context assemblers that can route context resolution requests to specialized capability URNs (`balance`, `ledger`, `jobwork`, `exception`). Basic `SemanticResolverRegistry` mechanics have been built in CEM to translate strings to UUIDs.

## 7. Existing Architectural Gaps
- **Lack of Nuanced Requirement Classification**: Missing attributes are typically treated as failures instead of being categorized as derivable, broadenable, or optional.
- **Rigid Error Handling**: If multiple candidate entities are found during string-to-UUID resolution, the system often timeouts (504) or fails instead of bubbling up ambiguous candidate options back to the Brain.
- **Zero Broadening capability**: If an optional parameter (like Warehouse) is absent, the system doesn't intelligently expand the query (e.g., aggregating stock across all warehouses).
- **Hard-failed Clarification**: Clarification is not a progressive conversational step but instead a hard block due to unresolvable inputs.

## 8. Root Causes
The orchestration pipeline assumes a deterministic, structured data-retrieval pattern inherited from standard API interactions, instead of treating data retrieval as a conversational, fuzzy exploration process.

## 9. Rabta Objective
To enable an intelligent bridge where natural language seamlessly resolves into authoritative business truth. The system must prioritize maximum useful, truthful answers from available evidence, relying on progressive query expansion, candidate generation, and minimal clarification, without ever exposing the underlying database schema to the user or Brain Core.

## 10. Target Architecture
Rabta is NOT a strictly linear pipeline. Rabta introduces ONE BOUNDED REFINEMENT LOOP into the existing Brain Core + IID + CEM lifecycle.

The fundamental lifecycle is:
1. **USER** -> provides natural language
2. **Brain Core + IID** -> conversational understanding / requirement reasoning (R-1, R-2)
3. **Brain -> CEM** -> abstract evidence request (R-3)
4. **CEM** -> business discovery / resolution / execution (R-4, R-5, R-7)
5. **CEM -> Brain** -> returns evidence + candidates + capabilities + gaps
6. **Brain Core + IID** -> reasons over the returned business evidence (R-8)
7. **Refinement Decision**: Is refinement genuinely necessary?
   - **YES**: ONE refined CEM request is issued (R-6) -> CEM FINAL execution -> Evidence -> User
   - **NO**: Final interpretation -> User

## 11. Brain Core / CEM / Intelligence Domain Responsibility Boundary
RABTA is a generic cognitive/protocol architecture. It does NOT contain business truth. 
The applicable Intelligence Domain (ID) and Context Execution Module (CEM) are integration participants selected by the surrounding system; they are not intrinsic dependencies of RABTA.

- **RABTA**: The generic cognitive protocol and orchestration model. It defines reusable responsibilities/capabilities (R-1 through R-11), not a fixed, domain-specific module-to-module call sequence. RABTA MUST be agnostic to both the ID and the CEM participating in a request. It must not hardcode, import, instantiate, or otherwise depend on a specific ID or CEM.
- **BRAIN CORE**: Implements the RABTA orchestration. Owns generic conversational reasoning (R-2) and orchestration (R-3). Has NO business schema knowledge, NO physical identifier knowledge, and NO domain-specific rules.
- **INTELLIGENCE DOMAIN (ID)**: The domain intelligence provider. An ID's participation is conditional, not mandatory at every lifecycle point. It may participate before (R-1) and/or after (R-8, R-9) CEM execution when domain-specific understanding, interpretation, decision, or action is required. R-1 understanding may be produced by the applicable ID, but RABTA contracts remain ID-agnostic.
- **CEM (Context Execution Module)**: The business reality/execution provider. R-4/R-5/R-7 (discovery, resolution, execution) may be provided by the applicable CEM, but RABTA contracts remain CEM-agnostic. CEM reports business facts from the authoritative business system.

## 12. Requirement Classification Model
Brain's initial classification is based on conversational/domain meaning. Where execution feasibility depends on CEM knowledge, Brain must not pretend to know the answer before CEM responds.

### MANDATORY
Execution cannot safely proceed without it.
### OPTIONAL
Its presence increases precision, but absence does not block execution.
### DERIVABLE
The requirement can be derived from available evidence/context.
### BROADENABLE
Its absence permits execution at a broader valid scope. "Warehouse omitted" must NOT automatically become MANDATORY nor BROADENABLE until the architecture has sufficient execution context to establish what the CEM can actually provide. The architecture should permit "potentially broadenable" during initial reasoning.
### AMBIGUOUS
Multiple materially different interpretations exist.
### UNRESOLVED
Execution genuinely cannot safely proceed.

## 13. Rabta Architectural Principles
- **Schema Independence**: Brain Core must never know the database columns or internal physical structures.
- **Entity Resolution**: The specific CEM resolves human-readable identifiers into physical candidates. RABTA merely defines the protocol.
- **Clarification**: Must be a last resort.
- **Broadening**: Safely expand queries when precision is unavailable but truthful execution remains possible.
- **ID and CEM Agnosticism**: RABTA MUST be agnostic to both the Intelligence Domain (ID) and the Context Execution Module (CEM) participating in a request.
- **One Bounded Refinement Loop**: The loop must remain generic:
  1. Brain/RABTA understands context (optionally via applicable ID).
  2. Brain/RABTA requests evidence (R-3).
  3. Applicable CEM discovers, resolves, and executes (R-4, R-5, R-7) and returns facts.
  4. Brain/RABTA (optionally via applicable ID) interprets the facts (R-8) and decides if a single refinement pass (R-6) is required.
  5. If refined, applicable CEM executes the final pass.
  The loop must not assume Inventory, Sales, Orders, or any particular domain. No unrestricted recursion is allowed.

## 13b. Critical Reusability Test
RABTA contracts remain generic across domains. 
- **Inventory CEM**: Implements R-4/R-5/R-7 against the Inventory DB.
- **Sales CEM**: Implements R-4/R-5/R-7 against a CRM/Sales DB.
- **Order CEM**: Implements R-4/R-5/R-7 against an Order Management System.
The RABTA protocol (R-1, R-2, R-3) does NOT change when plugging in a new CEM. Only the CEM-side business implementation changes.

## 14. Loop Termination Rule
Rabta may perform an INITIAL CEM PASS + ONE REFINEMENT CEM PASS. Then it MUST terminate.
Possible terminal states:
- ANSWER
- CANDIDATES / USER SELECTION
- CLARIFICATION_REQUIRED
- PARTIAL_RESULT
- UNRESOLVED
- ACTION / ESCALATION where applicable

There must be no uncontrolled recursion.

## 15. Conversational Behaviour Principles
Optimize for the maximum useful, truthful answer with the minimum necessary clarification. Do not expose internal schema terminology to the user. Do not turn every imperfect query into a clarification step. Let the business system adapt to the user's language.

## 16. Current vs Target Behaviour
- **Current**: Exact-match failure when missing or misspelling parameters.
- **Target**: Graceful candidate generation, typo correction, or progressive broadening of scope.

## 17. Query Behaviour Matrix
| Query Family | Current Behaviour | Current Architectural Reason | Target Rabta Behaviour | Responsible Phase | Responsible Module |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1. Exact SKU | Succeeds if valid UUID/String | Semantic translation acts as 1:1 map | Succeeds | R-5 | CEM |
| 2. Product name | Fails or hangs (504) | CEM lacks 1:N string matching handlers | Resolves to candidates/IDs | R-5 | CEM |
| 3. Partial name | Fails | Exact matches required by CEM constraints | Fuzzy matching / Candidates | R-5 | CEM |
| 4. Typo | Fails | No fuzzy resolution layer active | Spell check / Typo correction | R-5 | CEM |
| 5. Fuzzy match | Fails | Explicit EQUALS operators | Candidate generation / IN operator | R-5 | CEM |
| 6. Attribute query | Unhandled | Capability expects distinct entity IDs | Schema-agnostic attribute mapping | R-4 | CEM |
| 7. Unknown entity | Fails | Missing fallback logic | Graceful failure / Clarification | R-8 | Brain/CEM |
| 8. Multiple candidates | Fails / Hangs | SemanticResolver expects scalar return | Returns candidate list to Brain | R-5 | CEM |
| 9. Broad scope | Fails | Missing Mandatory checks block execution | Progressively broadens query | R-6 | Brain/CEM |
| 10. Missing optional | Fails / Errors | Inflexible intent parser | Defaults to broadened execution | R-2 | Brain Core |
| 11. Missing mandatory | Blocks / Crashes | Not correctly classified as UNRESOLVED | Requests specific clarification | R-8 | Brain/IID |
| 12. Derivable info | Requested manually | Brain cannot chain context | Automates derivation from context | R-2 | Brain Core |
| 13. Ambiguous info | Hangs | Handlers assume perfect uniqueness | Pauses for user candidate selection | R-8 | Brain/IID |
| 14. Unresolved info | Returns execution error | Lacks UNRESOLVED classification | Clean fallback response | R-2 | Brain Core |
| 15. User decisions | N/A | IID doesn't persist multi-turn context | Decision engine integration | R-9 | IID |
| 16. Rich operator | Often errors | Restricted operator whitelist | Safe logical operator translation | R-5 | CEM |
| 17. Cross-attribute | Fails | Complex multi-intent unsupported | Compound constraint execution | R-7 | CEM |

## 18. Rabta Phase Roadmap
Rabta phases describe responsibilities and architectural capabilities, not necessarily a strictly sequential runtime pipeline. A simple query may complete after the first CEM pass. A difficult query may require the one permitted refinement.

- **R-0**: Architecture & Principles
- **R-1**: Conversational Understanding
- **R-2**: Requirement Classification / Reasoning
- **R-3**: Capability & Evidence Request
- **R-4.0**: Generic CEM Abstraction (Brain Core defined contract)
- **R-4**: Business Discovery (CEM implementation)
- **R-5**: Entity & Value Resolution (CEM implementation)
- **R-7**: Evidence Execution (CEM implementation)
- **CEM Feedback** (Evidence, candidates, capabilities, gaps returned to Brain)
- **R-6**: Progressive Query Expansion / Refinement Decision (OPTIONAL ONE-TIME REFINEMENT -> Loop back to R-4/R-5/R-7 if needed)
- **R-8**: Interpretation & Response
- **R-9**: Decision & Action
- **R-10**: Memory & Continuity
- **R-11**: End-to-End Certification

## 19. Phase Ownership
| Phase | Ownership | Responsibility |
| :--- | :--- | :--- |
| **R-1** Conversational Understanding | **IID** | Extracts intent and components from user input. |
| **R-2** Requirement Classification | **Brain Core** | Evaluates conversational necessity. |
| **R-3** Capability/Evidence Request | **Brain Core** | Protocol definition & abstract transmission. |
| **R-4.0** Generic CEM Abstraction | **Brain Core** | Defines the reusable CEM template/contract. |
| **R-4** Business Discovery | **CEM (Implementation)** | Authoritatively maps request to physical capabilities. |
| **R-5** Entity/Value Resolution | **CEM (Implementation)** | Resolves semantic strings to opaque physical identifiers. |
| **R-6** Progressive Expansion | **Shared** | Brain requests broader execution; CEM executes it. |
| **R-7** Evidence Execution | **CEM (Implementation)** | Executes capability against business truth. |
| **R-8** Interpretation | **Brain Core / IID** | Interprets business facts returned by CEM. |
| **R-9** Decision & Action | **IID** | Domain-specific follow-ups and actions. |
| **R-10** Memory & Continuity | **Shared** | Persists resolved entities for conversation context. |
| **R-11** E2E Certification | **Shared** | - |

## 20. Architectural Decisions
1. **Decision:** CEM controls semantic-to-system identifier resolution via Registry/Middleware.
   **Reason:** Keeps Brain Core strictly decoupled from physical constraints.
   **Consequence:** CEM must handle fuzzy matching, 1:N mapping, and typo correction internally.
   **Owner:** CEM
   **Phase:** R-5
   **Status:** APPROVED

2. **Decision:** Omitted optional parameters result in progressive broadening, not clarification blocks.
   **Reason:** Optimize for "maximum useful, truthful answer".
   **Consequence:** Business logic handlers must support broad scope execution safely.
   **Owner:** Brain/CEM
   **Phase:** R-6
   **Status:** APPROVED

3. **Decision:** Rabta uses one bounded refinement loop.
   **Reason:** A one-pass execution cannot support genuinely open-ended conversational interaction because Brain initially lacks business-system reality, while CEM lacks conversational/domain reasoning.
   **Consequence:** The first CEM pass may return business evidence, candidates, capabilities and gaps. Brain + applicable ID may refine the request once. No unrestricted recursive execution is permitted. The loop remains completely domain-agnostic.
   **Owner:** Brain/CEM
   **Phase:** R-0 architectural pivot
   **Status:** APPROVED

4. **Decision:** CEM Implementation Ownership (R-4, R-5, R-7).
   **Reason:** RABTA is a generic cognitive/protocol layer. If RABTA implemented R-4 (Business Discovery), it would become heavily coupled to specific schemas and lose reusability.
   **Consequence:** R-4, R-5, and R-7 are protocol boundaries defined by RABTA, but their physical implementation lives entirely within the applicable CEM. Brain Core will never contain SQL or fuzzy matching logic.
   **Owner:** CEM
   **Phase:** R-4/R-5/R-7
   **Status:** APPROVED

5. **Decision:** RABTA ID and CEM Agnosticism.
   **Reason:** RABTA must serve as a generic protocol and orchestration model. Hardcoding dependencies on specific IDs or CEMs prevents multi-domain scaling.
   **Consequence:** RABTA must not hardcode, import, instantiate, or otherwise depend on a specific ID or CEM. ID participation is conditional. R-1 through R-11 describe reusable responsibilities, not a fixed module-to-module call sequence.
   **Owner:** RABTA
   **Phase:** R-0 architectural clarification
   **Status:** APPROVED

## 21. Open Questions
- A. How does Brain communicate an abstract requirement to CEM?
- B. How does CEM expose what it can actually execute?
- C. How does CEM discover its own schema?
- D. How does CEM map semantic concepts to physical types?
- E. How does CEM resolve names into internal identifiers?
- F. How does the system handle multiple candidates?
- G. How does the system determine whether missing information is mandatory or optional?
- H. How does the system determine whether a broader query is safe?
- I. How does the system represent confidence?
- J. How does the system return partial evidence?
- K. How does the system communicate unresolved information?
- L. How does Brain distinguish "no data" from "no capability"?
- M. How does the system prevent LLM hallucination from becoming business truth?
- N. How does conversational context influence subsequent queries?
- O. How are user corrections remembered?
- P. How are resolved entities reused within a conversation?
- Q. How does the architecture avoid recursive Brain -> CEM -> Brain loops unless genuinely required?
- R. How does the system avoid repeatedly parsing the same query boundary?
- S. How can the architecture remain domain-independent as new CEMs are added?

## 22. Phase History
R-0 — PIVOT TO BOUNDED LOOP
R-1 — Conversational Understanding (COMPLETED)
R-2 — Requirement Classification (COMPLETED)
R-3 — Capability & Evidence Request (COMPLETED)

### R-2 Implementation Summary
- **Implementation**: R-2 was implemented as an LLM-assisted generic classification step (`RequirementClassifier`). It strictly evaluates conversational necessity without guessing execution feasibility.
- **Architectural Decisions**: 
  1. R-2 does NOT assign `BROADENABLE` based on missing components; this is deferred to R-6 execution stages. 
  2. R-2 never invents fields; it only classifies what R-1 provides.
  3. No global default classification is enforced (it remains nullable).
- **Files Changed**: `src/shared/requirement_classification_contracts.py`, `src/brain_core/classification/classifier.py`, `src/intelligence_domains/inventory_intelligence/orchestrator.py`, `tests/rabta/test_r2_classification.py`.
- **Tests/Results**: 100% test coverage (6 tests explicitly targeting R-2 boundary behaviors). 131/131 total regression tests passed.
- **Limitations**: The LLM parsing relies on strict json blocks and a fallback heuristic if parsing fails. Broadenable concepts are deferred until after CEM discovery.
- **Deviation from Approved Design**: None.

### R-3 Implementation Summary
- **Implementation**: Created the Pydantic contracts `AbstractEvidenceRequest` and `BusinessEvidenceResponse` to govern the Brain-CEM interaction boundary.
- **Architectural Decisions**:
  1. `AbstractEvidenceRequest` embeds `ClassifiedRequirement` fully to prevent conversational loss.
  2. CEM returns factual statuses (e.g., `MULTIPLE_CANDIDATES`, `EXECUTION_LIMITATION`) rather than prescriptive instructions (`NEEDS_REFINEMENT`).
  3. Physical identifiers (`business_id`) are returned as opaque strings; Brain treats them as opaque tokens for potential second passes (R-6) without acquiring schema knowledge.
- **Files Changed**: `src/shared/evidence_request_contracts.py`, `tests/rabta/test_r3_contracts.py`.
- **Tests/Results**: 100% boundary testing for structure integrity. 134/134 total regression tests passed.
- **Limitations**: Contracts are currently passive data structures awaiting R-4 implementation to actually wire Brain and CEM together.
- **Deviation from Approved Design**: None.

## 23. Certification Status
R-3 STATUS: READY FOR R-4

## 24. RABTA ARCHITECTURAL FREEZE: ID & CEM RESOLUTION

### 1. APPROVED ARCHITECTURE
RABTA/Brain Core acts as a pure, generic orchestrator of interfaces. It does not own physical routing, service discovery, or domain intelligence. 
- The Host Application explicitly requests an Intelligence Domain (`id_urn`) and a Context Execution Module (`cem_urn`).
- Brain Core authorizes the application's request to use these resources.
- Brain Core uses generic resolver interfaces (`IntelligenceDomainResolver`, `ContextExecutionResolver`) provided by the infrastructure to locate the concrete implementations.
- Intelligence Domains and CEMs have NO permanent architectural relationship to each other. They are completely decoupled by Brain Core.

### 2. REJECTED ALTERNATIVES
- **Identity owning cognitive routing (JWT Claims)**: Rejected. Conflates authentication with cognitive routing, forcing JWT re-issuance for application capability changes and burdening Identity with AZM ecosystem details.
- **ID dictating the CEM**: Rejected. IDs are purely cognitive. A single Inventory ID can serve an ERP application (using ERP CEM) or a standalone Mobile App (using Mobile CEM). The ID cannot know which physical CEM to route to.
- **Hardcoding registries in Brain Core**: Rejected. Brain Core must depend on resolver *interfaces*. The implementation (in-memory dict, gRPC, service mesh) belongs to the deployment infrastructure, not the cognitive core.
- **CEM URLs in R-3 Request**: Rejected. `AbstractEvidenceRequest` must remain purely semantic. Physical routing is handled entirely by the CEM Resolver and Adapter infrastructure.

### 3. EXACT OWNERSHIP MATRIX
| Responsibility | Owner |
| :--- | :--- |
| Application Identity & Authentication | AaramIdentity |
| Target `id_urn` & `cem_urn` Selection | Host Application (via API request) |
| Authorization (App → ID / App → CEM) | Brain Core (via Ecosystem Config/Authorizer) |
| R-1 (Conversational Understanding) | Applicable Intelligence Domain (ID) |
| R-2 & R-3 (Classification, Request) | Brain Core (RABTA) |
| ID / CEM Physical Resolution | Infrastructure (implementing Resolvers) |
| R-4, R-5, R-7 (Discovery, Execution) | Applicable Context Execution Module (CEM) |
| R-8 (Interpretation) | Brain Core + Applicable ID |

### 4. EXACT RUNTIME SEQUENCE
1. **Application** sends Query + AaramIdentity Token + `id_urn` + `cem_urn` to Brain Core.
2. **Brain Core** validates Token with AaramIdentity.
3. **Brain Core** authorizes the `client_id` to ensure it is permitted to invoke `id_urn` and `cem_urn`.
4. **Brain Core** calls `IntelligenceDomainResolver.resolve(id_urn)` to get the `IntelligenceDomainProvider`.
5. **Brain Core** invokes R-1 (`extract_understanding`) on the ID Provider.
6. **Brain Core** performs R-2 (Classification) and R-3 (Evidence Request generation).
7. **Brain Core** calls `ContextExecutionResolver.resolve(cem_urn)` to get the `ContextExecutionAdapter`.
8. **Brain Core** invokes execution on the CEM Adapter, passing `AbstractEvidenceRequest` and the auth context.
9. **CEM** executes R-4/R-5/R-7 and returns `BusinessEvidenceResponse`.
10. **Brain Core + ID** perform R-8 interpretation and decide if bounded refinement is necessary.
11. **Brain Core** returns the final answer to the Application.

### 5. ID RESOLUTION MODEL
Brain Core depends on a generic `IntelligenceDomainResolver` interface. The infrastructure provides the implementation, which maps the `id_urn` string requested by the application to a concrete `IntelligenceDomainProvider` interface capable of executing R-1 and R-8.

### 6. CEM RESOLUTION MODEL
Brain Core depends on a generic `ContextExecutionResolver` interface. The infrastructure provides the implementation, which maps the `cem_urn` string requested by the application (or derived from app context) to a concrete `ContextExecutionAdapter` capable of executing R-4/5/7. There is NO coupling between the ID and the CEM. Brain chooses the CEM solely based on the `cem_urn` resolved by the infrastructure.

### 7. AUTHORIZATION MODEL
AaramIdentity issues the authentication token proving the `client_id`. 
Brain Core infrastructure holds the authorization mapping (`client_id` → allowed `id_urn`s and `cem_urn`s). Brain Core enforces this authorization boundary before invoking any Resolvers, ensuring applications cannot execute against unauthorized CEMs or query unauthorized domains.

### 8. REQUIRED INTERFACES/CONTRACTS
Before R-4 can be implemented, the following interfaces must exist in `src/shared/rabta_interfaces.py`:
1. `IntelligenceDomainProvider`: Exposes `extract_understanding(query)` and `interpret_evidence(...)`. Must NOT know CEM execution details.
2. `IntelligenceDomainResolver`: Exposes `resolve(id_urn) -> IntelligenceDomainProvider`.
3. `ContextExecutionAdapter`: Exposes `execute_evidence_request(req, auth_context) -> BusinessEvidenceResponse`. Must NOT know R-1/R-2 logic.
4. `ContextExecutionResolver`: Exposes `resolve(cem_urn) -> ContextExecutionAdapter`.

None of the existing R-1/R-2/R-3 contracts (`ConversationalUnderstanding`, `ClassifiedRequirement`, `AbstractEvidenceRequest`) require modification. They must remain completely free of routing details, URLs, or specific database schemas.

### 9. WHAT REMAINS IMPLEMENTATION-SPECIFIC
- The actual implementation of the Resolvers (e.g., hardcoded dictionaries for MVP, Redis, or Kubernetes service discovery later).
- The actual implementation of the CEM Adapters (REST calls to standalone apps, direct DB connections, etc.).
- The storage mechanism for the Brain Core authorization mappings.

### 10. WHAT MUST NOT BE CHANGED
- AaramIdentity (No JWT schema changes).
- R-1, R-2, R-3 Pydantic models.
- The One-Bounded Refinement Loop principle.
- CEM business discovery logic (must not be moved into Brain or ID).

## 25. RABTA PHASE R-4.0: GENERIC CEM ABSTRACTION & CAPABILITY CONTRACT

### 1. PHASE PURPOSE
R-4.0 establishes the generic, CEM-agnostic and domain-agnostic abstraction boundary that any Context Execution Module must implement to participate in the RABTA ecosystem. R-4.0 is OWNED BY BRAIN CORE. It is not the implementation of business discovery itself, but rather the template and contract defining what a CEM must be capable of receiving and returning.

### 2. EXPLICIT RESPONSIBILITY BOUNDARIES
- **R-4.0 (Generic CEM Abstraction):** Owned by Brain Core. Defines the generic interface (`ContextExecutionAdapter`) and data contracts (`AbstractEvidenceRequest`, `BusinessEvidenceResponse`) without any physical schema knowledge, inventory concepts, URLs, or database specifics.
- **R-4 (Business Discovery):** Owned by the applicable CEM. The concrete implementation inside the CEM that inspects its own business reality based on the R-4.0 request.
- **R-5 (Entity Resolution):** Owned by the applicable CEM. Resolves semantic references to physical opaque business IDs during discovery.
- **R-7 (Execution):** Owned by the applicable CEM. Executes business side-effects if applicable.

### 3. THE R-4.0 ABSTRACTION CONTRACT
The R-4.0 contract is completely fulfilled by the existing generic `ContextExecutionAdapter` protocol and its associated Request/Response payload models.
- **Receives Evidence Request:** Through `AbstractEvidenceRequest`.
- **Participates in Refinement:** Through `AbstractEvidenceRequest.refinement_context`.
- **Exposes Capabilities/Absence:** Through `BusinessEvidenceResponse.capabilities_discovered` and `BusinessRealityStatus`.
- **Reports Candidate Entities:** Through `CandidateEntity` and `resolved_candidates`, returning opaque string `business_id`s that Brain treats natively without schema assumptions.
- **Reports Factual Limitations:** Through `ExecutionLimitation`.
- **Returns Evidence Data:** Through `BusinessEvidenceResponse.evidence_data` when execution completes.

### 4. R-4 READINESS CRITERIA
Concrete R-4 (Business Discovery) inside a specific CEM is GO when:
1. The RABTA architecture proves `ContextExecutionAdapter` can be implemented by a completely neutral mock without data loss.
2. The orchestrator tests prove no domain-specific leakage occurs at the boundary.
3. The regression suite passes fully against the frozen abstract contract.

## 26. RABTA BASELINE CERTIFICATION (R-4 through R-11)

### A. RABTA Baseline Status
- **RABTA BASELINE CERTIFIED**
- R-4 through R-10 implemented and certified as applicable.
- R-11 completed end-to-end certification.
- The RABTA baseline is now **FROZEN**.

### B. R-9: Decision & Action Safety
- **DecisionEngine**: Generic interceptor for mutative requests.
- **Destructive-Action Confirmation**: Intercepts `intent=ACTION` before passing to R-7.
- **Explicit Confirmation/Rejection**: Uses conversational intents to manage pending state.
- **Suspended Actions**: Holds requests securely via R-10.
- **Atomic Consumption**: Ensures exactly-once execution.
- **Duplicate/Concurrent Confirmation Protection**: PostgreSQL atomic `UPDATE` with `rowcount == 1`.
- **Proactive Recommendations**: Derives recommendations safely from factual business evidence.
- **Recommendation Confirmation Before Execution**: Recommendations cannot bypass the suspension and confirmation boundaries.

### C. R-10: Memory & Continuity
- **ConversationSession / ConversationTurn**: Persists normal conversational history.
- **SuspendedExecutionState**: Strictly separates pending actions from general history.
- **MemoryProvider**: Generic interface for persistence operations.
- **Orchestrator Continuity**: `RabtaOrchestrator` integrates R-10 for session-aware context.
- **PostgreSQL Persistence**: `PgVectorMemoryAdapter` backs the interface.
- **TTL**: Strict time-to-live enforcement for pending actions.
- **Atomic Consume**: Prevents race conditions during execution.
- **Session/User/Tenant Isolation**: Enforces explicit access boundaries via `session_id`.

### D. R-8: Interpretation & Response
- **ConversationalResponse**: Contract for final structural output to the user.
- **InventoryInterpreter**: Resolves abstract `BusinessEvidenceResponse` data to domain-specific natural language.
- **Deterministic Interpretation**: Relies purely on CEM facts without generative AI hallucination.
- **Clarification Handling**: Generates structural refinement prompts for the user.

### E. R-7: Business Execution
- **Typed Action Parameters**: Strict `TypedActionParameter` definitions for safety.
- **Action Adapters**: Context execution handlers for mutations.
- **Domain Exception Boundary**: Strict error containment.
- **No Broad Exception Masking**: Bubbles up fatal errors structurally.
- **Transformation and Stock Adjustment**: Intentionally blocked from the current baseline release.

### F. R-6: Progressive Expansion & Refinement
- **Bounded Refinement**: Exact one-pass execution loop to prevent recursive runaway logic.
- **Execution Limitation Handling**: Safe handling of `EXECUTION_LIMITATION` statuses.
- **Clarification/Refinement Boundary**: Clear transition to R-8 when automated refinement fails.

### G. R-11: End-to-End Certification
- All 14 required end-to-end flows certified.
- **No certification blockers**.
- **No conditions before freeze**.

### H. Known Non-Blocking Finding
- The legacy `InventoryCemAdapter` exhibits a mismatch, passing `evidence` instead of the authoritative `evidence_data`.
- This was explicitly classified as **NON-BLOCKING** by the R-11 audit.
- It is safely normalized by R-8/R-9 and does not constitute an architectural blocker.

### I. Post-Certification Rule
**RABTA CORE IS FROZEN.**
Future work should onboard Intelligence Domains and business capabilities using the frozen contracts, rather than creating unnecessary new RABTA architecture phases.
