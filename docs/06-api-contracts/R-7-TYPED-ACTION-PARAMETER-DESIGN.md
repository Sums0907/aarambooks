# R-7 TYPED ACTION PARAMETER DESIGN

**Workspace: AaramBrain**

## 1. Current Problem
R-7 (Business Execution) is BLOCKED. 
The current `AbstractEvidenceRequest` relies on the `ConversationalUnderstanding` AST, which models parameters loosely in `SemanticCondition` (using `value: Any`) or `SemanticAttribute` (using raw strings). To construct strict domain DTOs for ACTION intents (like Goods Receipt or Job Work Issue), R-7 would be forced to interpret raw conversational strings (e.g., "50 units", "next Tuesday") via NLP. This severely violates the RABTA decoupling principles: R-7 is a physical execution boundary and must never act as a conversational parser.

## 2. Existing Contract Analysis
Currently, `ConversationalUnderstanding` represents:
- **Entities**: Strongly modeled as `SemanticEntityReference` (resolved via R-5 into opaque `business_id`s).
- **Intent**: Strongly modeled via `ConversationalIntent` enum (`ACTION`, `RETRIEVE`, etc.).
- **Scalar Values**: Scattered. Modeled weakly inside `SemanticCondition.value` (typed `Any`) or `SemanticAttribute.original_expression` (typed `str`).
- **Temporal Values**: Treated the same as scalar values (weakly typed strings).
- **Refinement Context**: Handled by `AbstractEvidenceRequest.refinement_context`, carrying opaque `business_id`s and instructions.

The existing contract correctly models the *conversational structure* but completely lacks a deterministic, normalized *type structure* required for reliable execution.

## 3. Candidate Designs Considered
- **A. Explicit `ActionParameters` in `AbstractEvidenceRequest`:** Create a new dictionary or structure at the highest level specifically for ACTION requests. 
  *Pros:* Clean separation. *Cons:* Fragments the semantic payload; R-2 classification would have to straddle two different objects.
- **B. Typed `SemanticCondition.value` (Wrapper object):** Change `Any` to a `TypedScalar` object within conditions.
  *Pros:* Reuses existing fields. *Cons:* Conflates execution parameters with search filters.
- **C. New `NormalizedScalar` list in `ConversationalUnderstanding`:** Treat normalized action parameters as first-class citizens alongside `entities` and `conditions`.
  *Pros:* Preserves existing fields, perfectly segregates R-5 targets (entities) from R-7 targets (scalars), and allows R-2 to classify them cleanly.

## 4. Recommended Design
**Design C: Introduce `NormalizedParameter` to `ConversationalUnderstanding`.**
We add a strictly typed `parameters: List[NormalizedParameter]` array to `ConversationalUnderstanding`. Brain Core (or the Intelligence Domain during R-1) assumes full responsibility for parsing conversational text into these typed primitives. R-7 simply consumes them.

## 5. Typed Parameter Model
```python
from enum import Enum
from typing import Any
from pydantic import BaseModel

class ParameterDataType(str, Enum):
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"
    STRING = "STRING"

class NormalizedParameter(BaseModel):
    parameter_name: str           # e.g., "inventory.numeric.quantity"
    data_type: ParameterDataType  # Strict enforcement of expected type
    value: Any                    # Pydantic will validate based on data_type rules 
    original_expression: str      # e.g., "50 units" (kept for transparency)
```

## 6. ENTITY vs SCALAR vs TEMPORAL Boundary
- **ENTITY (`SemanticEntityReference`)**: An abstract, fuzzy reference (e.g., "Warehouse Y") that **requires R-5 resolution** to yield a physical `business_id` (UUID).
- **SCALAR (`NormalizedParameter`)**: A primitive, normalized value (e.g., `50.0`, `True`, `"PO-1234"`) that requires **no resolution**. It is passed directly to the domain DTO.
- **TEMPORAL**: Modeled as a `SCALAR` with a specific `ParameterDataType` (`DATE` or `DATETIME`). Dates are not entities; they do not need UUIDs. They simply require normalized parsing by Brain Core (e.g., `2026-08-29`).

## 7. R-6 Compatibility
This design is fully compatible with the R-6 Bounded Refinement Loop. If a request is progressively broadened or refined, Brain Core simply forwards the `NormalizedParameter` objects without re-parsing them. Because they are strictly typed, they survive the refinement loop identically to the opaque UUIDs.

## 8. Backward Compatibility
- **R-2, R-3:** Fully compatible. `NormalizedParameter` can be classified as `MANDATORY` or `OPTIONAL` exactly like entities.
- **R-4, R-5:** Fully compatible. `RETRIEVE` queries can ignore the `parameters` array or use it as strict filters, maintaining legacy support.
- **Legacy Stage F:** Will not break, as the new field defaults to an empty list `[]`.

## 9. Example ACTION Payloads (Conceptual)

**Goods Receipt (SKU + warehouse + quantity):**
- `entities`: [`SemanticEntityReference(original_expression="SKU X")`, `SemanticEntityReference(original_expression="Warehouse Y")`]
- `parameters`: [
    `NormalizedParameter(parameter_name="inventory.numeric.quantity", data_type=DECIMAL, value=50.0)`
  ]

**Stock Adjustment (SKU + warehouse + quantity + movement type):**
- `entities`: [`SemanticEntityReference("SKU X")`, `SemanticEntityReference("Warehouse Y")`]
- `parameters`: [
    `NormalizedParameter(parameter_name="inventory.numeric.quantity", data_type=DECIMAL, value=10.0)`,
    `NormalizedParameter(parameter_name="inventory.movement.direction", data_type=STRING, value="OUT")`
  ]

**Job Work Issue (SKU + job worker + quantity):**
- `entities`: [`SemanticEntityReference("SKU X")`, `SemanticEntityReference("Vendor Z")`]
- `parameters`: [
    `NormalizedParameter(parameter_name="inventory.numeric.quantity", data_type=DECIMAL, value=100.0)`
  ]

## 10. Validation Ownership
- **Brain Core / ID (R-1/R-2):** Owns parsing conversational text ("50 units") into a normalized primitive (`50.0`) and assigning the correct `data_type` and semantic identifier.
- **Brain Core (R-3):** Validates the structural integrity of the primitive type against the declared `data_type`.
- **R-5 (CEM):** Owns the resolution of fuzzy Entities to UUIDs.
- **R-7 (CEM):** Owns final Domain Business Validation (e.g., "Is 50.0 within acceptable bounds?", "Are all REQUIRED fields present for a Goods Receipt?").

## 11. Files That Would Change (If Approved)
- `src/shared/conversational_contracts.py` (Add `NormalizedParameter`, `ParameterDataType`, and update `ConversationalUnderstanding`).
- `tests/rabta/test_r1_understanding.py` (To test the new parameter structures).

## 12. R-7 Unblocking Criteria
R-7 adapter implementation may begin ONLY when:
1. `NormalizedParameter` is officially merged into `conversational_contracts.py`.
2. The R-1 intent parser (Intelligence Domain) is updated to emit `NormalizedParameter` for quantities, dates, and booleans.
3. Tests prove that Brain Core can successfully transmit these strict primitives over the R-3 boundary without data loss.

## 13. Exact Next Step
Implement the `NormalizedParameter` contract extension in `src/shared/conversational_contracts.py` within the Brain Core workspace.
