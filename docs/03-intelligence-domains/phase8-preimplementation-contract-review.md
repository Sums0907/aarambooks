# Phase 8 Pre-Implementation Contract Review

## 1. Authoritative Phase 8 Scope
Phase 8 entails building the domain-specific intelligence orchestration loops for NDR (Non-Delivery Reports) and Customer Queries. These loops are responsible for evaluating business context, reasoning over intents and failure reasons, interacting with the customer, and outputting explicit, deterministic action requests.
- **NDR Intelligence Scope:** Handling the end-to-end lifecycle of an NDR case (understanding the failure, gathering context, generating a resolution decision, communicating with the customer if necessary, and outputting an `ActionRequest`).
- **Customer Query Intelligence Scope:** Receiving customer messages, understanding semantic intent, fetching relevant policy/product knowledge, framing a conversational response, and outputting an `ActionRequest` if an operational change is warranted.
- **Explicitly OUT OF SCOPE:** Direct execution of refunds, altering operational data directly without an `ActionRequest`, maintaining master data for orders/customers, physical event bus implementation (webhooks/Kafka), and live telephony/helpdesk integration.

## 2. Existing Contracts Inspected
- `docs/AG_PROJECT_PHASES.md` & `docs/10-implementation-plan/implementation-backlog.md`
- `docs/03-intelligence-domains/ndr-intelligence/ndr-intelligence-technical-design.md`
- `docs/03-intelligence-domains/customer-query-intelligence/customer-query-intelligence-technical-design.md`
- `src/brain_core/models/contexts.py` (`CustomerContext`, `ShipmentContext`, etc.)
- `src/brain_core/action_engine/contracts.py` (`ActionRequest`, `ActionResponse`)
- `src/brain_core/decision/interfaces.py` (`DecisionRecommendation`, `DecisionAlternative`)
- `src/brain_core/gateway/interfaces.py` (`ModelGatewayProvider`)
- `src/brain_core/knowledge/interfaces.py` (`KnowledgeProvider`)
- `src/brain_core/memory/interfaces.py` (`MemoryProvider`)

## 3. NDR Intelligence Contract
- **Consumes:** `ShipmentContext` (failure reason, delivery attempts), `CustomerContext` (contact info, previous interaction history), `OrderContext` (order value), and `KnowledgeResult` (courier rules).
- **Produces:** `ActionRequest` (e.g., parameterizing a retry or address change), `DecisionRecommendation` (tracking the AI's internal justification), and conversational strings meant for customer outreach.

## 4. Customer Query Intelligence Contract
- **Consumes:** Raw inbound customer queries, `CustomerContext` (profile, past issues), `OrderContext` (status), and `KnowledgeResult` (store policies, FAQs).
- **Produces:** Conversational response strings, `DecisionRecommendation` (classifying the intent and response approach), and `ActionRequest` (e.g., initiating a return workflow).

## 5. Brain Core Dependency Map
- **ContextAssembler:** Used to fuse raw inputs into `FrozenContextModel` instances.
- **ModelGatewayProvider:** Used exclusively for executing LLM reasoning prompts (intent extraction, decision selection).
- **KnowledgeProvider:** Searched to retrieve organizational SOPs to inject into LLM prompts.
- **MemoryProvider:** Used to log and retrieve the `ConversationSession` and historical `DecisionRecommendation`s.
- **ActionEngine Schemas:** Output `ActionRequest` with explicit `ActionCategory` (e.g., `SUGGESTED_RESOLUTION`, `HUMAN_ASSISTANCE`).

## 6. LLM Boundary
- The Gemini model MUST NOT be accessed directly via SDK; all inference goes through `ModelGatewayProvider.generate`.
- The LLM acts purely as a reasoning and extraction engine. It MUST NOT invent order states, customer facts, or business rules.
- Authoritative operational truth (e.g., "Refund policy is 30 days") must be explicitly injected into the prompt via `KnowledgeResult` and `ContextModel`s.
- Decisions must remain governed; the LLM merely selects from predefined alternatives and its output is parsed into a strict `DecisionRecommendation` object.

## 7. Synthetic Fixture Requirements
Because Phase 8 is "Synthetic Development", deterministic JSON fixtures must be used for testing:
- **Happy Paths:** Valid `OrderContext` and `CustomerContext` for simple "where is my order" queries.
- **NDR Scenarios:** `ShipmentContext` with "Customer Not Available" attempt logs.
- **Missing/Ambiguous Context:** Queries about non-existent `order_id`s.
- **Escalation:** Scenarios triggering `ActionCategory.HUMAN_ASSISTANCE` (e.g., highly negative sentiment, high-value order disputes).
- **Hallucination-Sensitive:** Contexts with strict "NO REFUNDS" knowledge injected to ensure the LLM does not hallucinate a refund `ActionRequest`.

## 8. Test Strategy
- The test strategy must be strictly deterministic E2E unit testing of the orchestration logic.
- Real Gemini API calls are NOT required (and typically prohibited in fast CI unit tests). `ModelGatewayProvider` must be mocked/stubbed to return predefined `GatewayGenerationResponse` JSON structures.
- Tests will assert that given a frozen `CustomerContext` and mocked LLM intent extraction, the orchestrator successfully generates the expected `ActionRequest` with the correct parameters.

## 9. File-Level Implementation Matrix

| FILE | CREATE/MODIFY | PURPOSE | INPUT CONTRACT | OUTPUT CONTRACT | TEST REQUIRED |
|---|---|---|---|---|---|
| `src/intelligence_domains/ndr/orchestrator.py` | CREATE | NDR lifecycle loop | `ShipmentContext`, `CustomerContext` | `ActionRequest`, `DecisionRecommendation` | YES |
| `src/intelligence_domains/customer_query/orchestrator.py` | CREATE | Query lifecycle loop | `CustomerContext`, raw message | `ActionRequest`, string response | YES |
| `tests/fixtures/synthetic_contexts.json` | CREATE | Mock data | N/A | `CustomerContext`, `ShipmentContext` | NO |
| `tests/intelligence_domains/ndr/test_ndr_orchestration.py` | CREATE | Verify NDR logic | `synthetic_contexts.json`, Mocked Gateway | `ActionRequest` | NO |
| `tests/intelligence_domains/customer_query/test_query_orchestration.py` | CREATE | Verify query logic | `synthetic_contexts.json`, Mocked Gateway | `ActionRequest` | NO |
| `docs/10-implementation-plan/engineering-log.md` | MODIFY | Log Phase 8 progress | N/A | N/A | NO |

## 10. Phase Boundary / Prohibited Work
- **Phase 9 Restrictions:** Building physical inbound/outbound event boundaries (webhook listeners, REST APIs, Kafka producers/consumers) is strictly prohibited. Phase 8 orchestration functions must be callable as pure Python methods.
- **Phase 10 Restrictions:** Production deployment orchestration and cron scheduling must not be implemented.

## 11. Governance Conflicts
No conflicts found. The `implementation-backlog.md` explicitly aligns with the technical designs in stating that Phase 8 is "Synthetic Development" and relies on deterministic mock fixtures. The boundary separating intelligence from operational truth remains strictly defined across all documentation.

## 12. Final Readiness Verdict
READY TO IMPLEMENT
