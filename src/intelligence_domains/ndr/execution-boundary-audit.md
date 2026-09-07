# NDR-ID Execution Boundary Audit

This document answers the critical architectural question: **"What is the smallest REAL architectural boundary we need to build so that one NDR recovery recommendation can become a real business-system execution?"**

Based on a complete code and repository audit, the final V1 architecture has been explicitly defined to separate intelligence persistence from operational execution.

## EXPLICIT TERMINOLOGY & BOUNDARIES

1. **SHOPDECK MAIN ECOSYSTEM**
   - Real external ecosystem / real ShopDeck MCP.
   - **READ ONLY** for this project.
   - Manual human operator target. No autonomous mutation is permitted in V1.

2. **MOCK SHOPDECK BS**
   - Internal controlled Business System.
   - **WRITE CAPABLE**.
   - Used for architectural testing and owns the persistence of the canonical NDR Intelligence Result.

3. **NDR INTELLIGENCE RESULT**
   - Structured NDR intelligence output by the Brain Normalization Worker.
   - Persisted securely through the Mock ShopDeck BS API.

4. **NDR REPORT**
   - Operational artifact (CSV/PDF) generated deterministically from the Intelligence Result.
   - **NOT** Business Truth.
   - Used by the human operator to manually execute actions in the ShopDeck main ecosystem.

5. **AZM FEEDBACK/LEARNING**
   - **FUTURE** capability / Out of Scope for V1.

---

## A. Current Execution Architecture

The execution path for V1 strictly halts at the **NDR Action Report** boundary for the operator, and the **Mock ShopDeck BS Intelligence API** for data persistence.

1. **NDR Intelligence**: `src/intelligence_domains/ndr/orchestrator.py` generates an `ActionRequest`.
2. **Normalization Worker**: Persists the structured `IntelligenceResult`.
3. **Persistence**: Sent to `Mock ShopDeck BS` via `POST /api/v1/ndr/intelligence_results`.
4. **Report Generation**: The NDR Report Service projects the result into a CSV/PDF.
5. **Execution**: A human operator reviews the PDF and executes the action manually in the **ShopDeck main ecosystem**.

*Autonomous ShopDeck execution is explicitly OUT OF SCOPE for V1.*

## B. Action Capability Matrix

| NDR Action | Recommendation | Execution Possible (V1) | V1 Operational Target |
|---|---|---|---|
| `seller_reattempt` | YES | NO (Manual Only) | Human Operator via CSV/PDF |
| `address_enrichment_request` | YES | NO (Manual Only) | Human Operator via CSV/PDF |
| `courier_dispute` | YES | NO (Manual Only) | Human Operator via CSV/PDF |
| `offer_prepayment_incentive` | YES | NO (Manual Only) | Human Operator via CSV/PDF |

## C. Execution Observability (V1)

Execution observability terminates at the report level for V1:
- **AUTHORIZED**: Canonical Intelligence Result persisted in Mock ShopDeck BS.
- **PROJECTED**: CSV/PDF Report generated.
- **MANUAL ACTION**: Human operator marks `action_taken` in the CSV offline. (Not written back to DB in V1).

## D. Business Value Path (V1)

```text
REAL NDR EVENT
↓
REAL BUSINESS TRUTH (ShopDeck Main Ecosystem - Read Only)
↓
NDR INTELLIGENCE
↓
REAL RECOVERY RECOMMENDATION (Immutable Intelligence Result)
↓
MOCK SHOPDECK BS PERSISTENCE (Memory)  &&  NDR ACTION REPORT (Artifact)
↓
MANUAL HUMAN EXECUTION IN SHOPDECK MAIN ECOSYSTEM
```

## E. Future Execution (V2)
Autonomous execution of the `ActionRequest` via a dedicated adapter targeting the ShopDeck main ecosystem is deferred to V2. V1 establishes the intelligence memory and the operator-in-the-loop fallback.
