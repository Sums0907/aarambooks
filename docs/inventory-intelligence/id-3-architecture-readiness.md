# Phase ID-3: Inventory Semantic Knowledge (Policies & Reasoning) - Architecture Readiness

## 1. Current ID-3 Gap Analysis
In Phase ID-2, we successfully implemented **Intent Parsing**. The Inventory Intelligence Domain (ID) can now intercept unsupported queries and map supported queries to generic `EvidenceRequirement` objects using `CAPABILITY` concepts from Azm.
However, **Reasoning Synthesis** (Step 3 in the Orchestrator) currently relies on a hardcoded, generic system prompt ("DO NOT invent or estimate..."). 
**The Gap:** The ID does not dynamically load supported business policies or Standard Operating Procedures (SOPs) from Azm into its reasoning context. When the ID synthesizes the final answer from the `EvidencePackage`, it lacks the formal certified domain rules necessary for advanced synthesis.

## 2. Certified Semantic Knowledge Available
The authoritative source (`inventory-id-semantic-knowledge-source.md`) explicitly certifies the following domain rules and policies:

### Policies / SOPs Available
1. **Unique Stock Keeping:** Balances require both a SKU and a Warehouse to be definitively resolved.
2. **Movement Immutability:** Ledger movements are immutable once posted.
3. **Exception Source Tracking:** Exceptions must specify a source system (Accounting, Marketplace, Physical).
4. **Job Work Lifecycle:** Job work strictly tracks the lifecycle of Issued -> Consumed/Returned -> Pending.
5. **Confidence Scoring:** Balance records contain a system-generated confidence score.
6. **Exception State Machine:** Exceptions are governed by a strict state machine (`OPEN`, `INVESTIGATING`, `RESOLVED`).

## 3. Reasoning Context Requirements
The ID needs to inject these certified policies into the LLM during the **Reasoning / Synthesis** stage. 
When the LLM receives an `EvidencePackage` containing exceptions, it should know the Exception State Machine rules to properly describe the exceptions. When it receives a ledger, it should know about Immutability.

## 4. Existing Azm Support
**Supported:** The existing `AzmProvider` already supports storing concepts of type `"POLICY"`. Most of the certified policies are already seeded in the in-memory Azm mock (e.g., `inventory.policy.unique_balance`, `inventory.policy.immutable_movement`).

## 5. Existing ID-2 Overlap
Phase ID-2 already exposes:
- `get_certified_capabilities()`
- `get_unsupported_policies()`

ID-3 should *not* duplicate the `AzmProvider` interface. It merely needs a new method in `InventorySemanticKnowledge` (e.g., `get_supported_policies()`) to fetch the valid rules.

## 6. Unsupported / Explicit NOT-IN-SCOPE Items
The following business rules remain completely unsupported. The ID must NOT invent them during reasoning:
- Reorder Threshold Policies / Minimum Stock Levels
- Low-stock threshold logic
- Automated valuation / COGS policy (LIFO/FIFO)
- Jobwork aging escalation (e.g., >30 day rules)
- Negative-stock severity escalation
- Scrap/Wastage tracking (exists in DB, but not certified in CEM)

## 7. Exact Files Requiring Modification
1. `src/intelligence_domains/inventory_intelligence/knowledge.py`:
   - Add `get_supported_policies()` to return `POLICY` concepts where `status != UNSUPPORTED`.
2. `src/intelligence_domains/inventory_intelligence/orchestrator.py`:
   - Modify the `reasoning_prompt` in Step 3 (`REASONING`) to dynamically fetch supported policies from `self._knowledge.get_supported_policies()` and inject them into the system prompt.
3. `tests/intelligence_domains/inventory_intelligence/test_orchestrator.py`:
   - Add tests verifying that supported policies are successfully injected into the Gateway generation request during the Reasoning phase.

## 8. Dependencies & Boundary Risks
- **Dependencies:** None blocking. The `ModelGatewayProvider` and `AzmProvider` interfaces are fully sufficient.
- **Boundary Risks:** The LLM might attempt to misapply a supported policy to hallucinate an unsupported one (e.g., using "Confidence Score" to invent a "Severity"). The reasoning prompt must strictly bound the LLM to use the policies *only* to interpret the evidence provided.

## 9. Implementation Sequence for ID-3
1. Implement `get_supported_policies()` in `knowledge.py`.
2. Ensure any missing certified policies (like the Exception State Machine) are seeded in `azm_provider.py`.
3. Update `orchestrator.py`'s reasoning phase to concatenate and inject these policies into the `system_prompt`.
4. Write/Update tests to assert the reasoning prompt contains the dynamic policies.
5. Run test suite.

## 10. Verification / Test Plan
- Mock `AzmProvider` to return a specific supported policy.
- Trigger a supported query (e.g., "What are the exceptions?").
- Intercept the `GatewayGenerationRequest` during the reasoning phase and assert that the policy's description is present in the `system_prompt`.
- Ensure unsupported policies are NOT injected into the reasoning prompt.

## 11. Final Status
**READY**. All infrastructure and semantic knowledge boundaries from ID-1 and ID-2 are stable and capable of supporting ID-3 without any upstream architectural changes.
