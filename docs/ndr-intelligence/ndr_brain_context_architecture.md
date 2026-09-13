# NDR-ID BRAIN: Context Building & Future IVR Architecture

**Phase:** CONTEXT FOUNDATION ONLY
**Status:** Architecture Definition (No Execution)

---

## 1. Current Business System Architecture
ShopDeck operates as the authoritative Business System (BS). It maintains the operational ground truth for all shipments, NDRs, and historical actions in its Postgres database (`shipment_ndr_reports`, `ndr_action_log`). It ingests data from courier partners (and potentially legacy IVRs) via the ShopDeck MCP. The BS does not reason; it stores facts and executes authorized commands.

## 2. Exact Boundary between MCP / BS / Brain / IVR
The boundary is strictly governed to prevent the Brain from polluting the business reality:
* **ShopDeck MCP**: Upstream ingestion mechanism. Syncs raw courier updates into the Business System.
* **ShopDeck Business System**: The authoritative database. Normalizes MCP data into actionable facts.
* **NDR-ID Brain Context**: A read-only snapshot generated from the BS, isolating the Brain from raw databases.
* **Brain Decision**: The internal reasoning engine that produces a governed action request (not a direct mutation).
* **IVR Execution**: A separate executor that takes the Brain's governed proposal, validates it against the BS, and physically places the call.

## 3. NDR Canonical Data Model
An NDR case is not a flat status; it is a complex, temporal object. The canonical model must at minimum track:
- `awb_no` & `order_identifier`
- `latest_ndr_time` (defines the current cycle's temporal boundary)
- `ndr_count` (which attempt failed)
- `latest_ndr_reason`
- `ndr_status`
- `current_cycle_actions` (actions taken *after* `latest_ndr_time`)
- `historical_cycles` (actions taken *before* `latest_ndr_time`)
- Valid contact/phone details

## 4. NDR Cycle Model
NDRs must be modeled as repeated decision cycles, not permanent statuses.
**Lifecycle Rule:** A new failed delivery creates a strictly NEW decision cycle.
`NDR #1 -> Action -> Reattempt -> Fail -> NDR #2 (New Cycle)`
Historical actions from NDR #1 must *never* suppress the required action for NDR #2.

## 5. "Take Action" Semantics
"Take Action" is the primary actionable population. 
An NDR is classified as "Take Action" IF AND ONLY IF:
1. It is an active NDR.
2. There is NO qualifying action logged in the *current cycle* (after `latest_ndr_time`).

## 6. "Re-Attempt Requested" Semantics
"Re-Attempt Requested" is NOT a second action queue for the Brain. It is a waiting state.
If the Brain observes this state in the current cycle, it must wait. It only becomes actionable again if the reattempt physically fails, incrementing the `ndr_count` and spawning a new cycle.

## 7. Lifecycle: NDR → Reattempt → Failed → New NDR
1. **NDR #1** occurs.
2. Brain observes "Take Action", proposes IVR, customer agrees to Reattempt.
3. BS logs "Reattempt Requested". State is waiting.
4. If delivered: Close.
5. If failed: Courier syncs new failure. `ndr_count` increments. `latest_ndr_time` updates.
6. The old IVR action is now historically bounded. Brain sees a fresh, actionable NDR #2.

## 8. Required Brain Context
The Brain Context must answer exactly 10 questions and nothing else:
1. **WHO:** Customer name & contact.
2. **WHICH:** Order/AWB.
3. **WHY:** `latest_ndr_reason`.
4. **WHICH CYCLE:** `ndr_count`.
5. **WHAT HISTORY:** Previous actions in older cycles.
6. **WHAT CURRENT:** Actions already taken in *this* cycle.
7. **WHAT REQUIRED:** Is a decision needed now?
8. **WHAT SAFE:** What constraints exist (e.g. max 3 attempts).
9. **WHAT PROHIBITED:** What the Brain cannot do (e.g. call a 4th time).
10. **EVIDENCE:** Source timestamps proving freshness.

## 9. `NDR_BRAIN_CONTEXT_V1` Proposed Schema
```json
{
  "context_version": "1.0",
  "generated_at": "2026-09-13T10:00:00Z",
  "source_freshness": "2026-09-13T09:55:00Z",
  "identity": {
    "awb_no": "AWB123",
    "order_id": "NS999",
    "customer_name": "Ramesh",
    "contact_available": true
  },
  "cycle_data": {
    "current_ndr_cycle": 2,
    "latest_ndr_time": "2026-09-13T08:00:00Z",
    "latest_ndr_reason": "Customer Unavailable",
    "current_ndr_status": "open"
  },
  "action_history": {
    "current_cycle_actions": [],
    "historical_summary": ["NDR 1: IVR Placed -> Reattempt Requested"]
  },
  "actionability": {
    "is_actionable": true,
    "permitted_next_actions": ["propose_ivr", "propose_rto"]
  }
}
```

## 10. Fact vs. Derived vs. Inference Boundaries
- **FACT:** Supplied strictly by ShopDeck (e.g., `ndr_count = 2`, `reason = 'unavailable'`).
- **DERIVED FACT:** Deterministic math (e.g., `current_cycle_actions is empty` -> `is_actionable = true`).
- **INFERENCE:** Brain reasoning (e.g., "Customer is likely to answer an IVR").
- **ACTION DECISION:** Governed proposal (e.g., `propose_ivr`).
*Rule: Never present Brain inference as if it were a ShopDeck fact.*

## 11. Brain Decision Contract
The Brain does not mutate ShopDeck. It outputs a decision based on `NDR_BRAIN_CONTEXT_V1`. The decision is a stateless calculation that can run repeatedly without causing side effects.

## 12. IVR Action Proposal Contract
When reasoning concludes an IVR is needed, it yields an `IVR_ACTION_PROPOSAL`:
```json
{
  "action_type": "ivr_ndr_call",
  "awb_no": "AWB123",
  "ndr_cycle": 2,
  "reasoning_evidence": "Cycle 2 is actionable, reason is recoverable.",
  "objective": "Extract reattempt date",
  "allowed_outcomes": ["reschedule_agreed", "rto_confirmed"]
}
```

## 13. Idempotency Requirements
Brain reasoning may execute multiple times for the same state. To prevent spam:
- Proposals must contain a deterministic `idempotency_key` (e.g., hash of `awb_no` + `ndr_cycle`).
- The BS must reject execution if an action for `(awb_no, ndr_cycle)` already exists in `ndr_action_log`.

## 14. Execution Boundary
The Brain hands the `IVR_ACTION_PROPOSAL` to a Governance Gate. If approved, an independent IVR Executor physically dials the provider (Sarvam/Exotel). The Brain itself does NOT make network calls to Sarvam.

## 15. Result & Persistence Flow
1. IVR Executor places call.
2. Call completes -> Webhook received by Executor.
3. Executor formats result -> Writes strictly to ShopDeck BS (`ndr_action_log`).
4. Next MCP sync occurs -> Brain reevaluates the new context safely.

## 16. Failure Modes
- **Stale Context:** If `generated_at` is older than a strict threshold, Brain must abort reasoning.
- **Race Condition:** If Brain proposes IVR, but BS already logged a seller action, BS rejects the proposal (Idempotency).
- **Execution Failure:** If Sarvam fails, BS logs `IVR Failed`. Brain sees this as a current-cycle action and does not retry blindly.

## 17. Security & Authentication Considerations
- Brain must authenticate to BS using M2M tokens to request `NDR_BRAIN_CONTEXT_V1`.
- Action Proposals must be signed/authenticated so BS knows they originated from the governed Brain.

## 18. Future Roadmap
- **PHASE 1 (Current):** Build `NDR_BRAIN_CONTEXT_V1`.
- **PHASE 2:** Read-Only Brain (Reasoning without execution).
- **PHASE 3:** IVR Eligibility definitions.
- **PHASE 4:** Generate IVR Action Proposals.
- **PHASE 5:** Build IVR Executor.
- **PHASE 6:** Result Ingestion back to BS.
- **PHASE 7:** Closed-Loop Evaluation.
- **PHASE 8:** Optimization & Analytics.

## 19. Open Questions to Resolve Before IVR Execution
- How is the `idempotency_key` explicitly verified at the ShopDeck API boundary?
- What is the exact maximum latency tolerance between an NDR occurring and the Context being built?
- If the courier API goes down, how does the BS handle queued Reattempts?

## 20. Certification Criteria (Context → Execution)
Do not proceed to IVR Implementation until:
1. `NDR_BRAIN_CONTEXT_V1` can be successfully generated for 100 random production AWBs without hallucinated facts.
2. The Idempotency model is proven to block duplicate proposals for the same NDR Cycle.
3. The Business System's persistence loop for historical actions is verified to strictly adhere to `latest_ndr_time` boundaries.
