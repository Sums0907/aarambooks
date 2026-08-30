# R-7 PRE-IMPLEMENTATION CONTRACT STUDY — ACTION PAYLOAD SEMANTICS

**Workspace: AaramBrain**

## 1. Executive Conclusion
**BLOCKED**

The upstream semantic contract (`AbstractEvidenceRequest` / `ConversationalUnderstanding`) is currently insufficient for R-7 action execution. While it correctly represents fuzzy entity references (which R-5 resolves into physical UUIDs), it lacks a strongly-typed, non-conversational representation of scalar action parameters (quantities, dates, booleans, reference strings). If R-7 were implemented today, the CEM adapters would be forced to perform Natural Language Processing (NLP) to parse values like `"next Tuesday"` or `"50 units"` from `SemanticCondition` fields, severely violating the RABTA decoupling principles.

## 2. Current ACTION Request Structure
When Brain Core sends an ACTION request to the CEM, the payload is the `AbstractEvidenceRequest`. 

For the user meaning: *"Receive 50 units of SKU X into Warehouse Y"*
The values are currently scattered inside the `ConversationalUnderstanding` AST:

- **SKU (X)**: Appears in `entities` as a `SemanticEntityReference(original_expression="SKU X")`.
- **Warehouse (Y)**: Appears in `entities` as a `SemanticEntityReference(original_expression="Warehouse Y")`.
- **Quantity (50)**: Likely appears in `conditions` as `SemanticCondition(attribute_or_entity="quantity", operator="EQUALS", value="50 units")` or as a `SemanticAttribute`.
- **Date / Reference**: If omitted, they are absent. If provided (e.g., "today"), they appear as raw conversational strings in `conditions`.

## 3. Scalar Parameter Representation
**Are scalar values first-class semantic components?**
No. Scalar values are currently shoehorned into `SemanticCondition.value` (typed as `Any`) or `SemanticAttribute.original_expression` (typed as `str`). There is no mechanism guaranteeing that a quantity is parsed into a numeric type, or a date into ISO-8601. They remain as raw or semi-raw conversational text.

## 4. Entity Parameter Representation
Entities are correctly modeled as `SemanticEntityReference`. R-5 (Entity Resolution) successfully intercepts these and returns opaque `business_id` (UUID) tokens in the `resolved_candidates` payload. This portion of the contract is sound.

## 5. Scalar Normalization Ownership
**Who owns scalar normalization?**
Architecturally, **Brain Core / Intelligence Domain** must own scalar normalization. 
R-7 (CEM) is a physical execution module; it executes structured facts against a database. It must not parse natural language. The conversion of conversational values (e.g., "50 units" → `Decimal("50")`, "next Tuesday" → `2026-09-01`) must occur in the cognitive layers (R-1 intent extraction or R-3 request formulation) before crossing the boundary into the CEM.

## 6. Seven Capability DTO Requirement Matrix

| Capability | Required Fields | Entity / Scalar | Source in Current Brain Core | Requires R-5? | Requires Typed Normalization? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Goods Receipt** | SKU, Warehouse | Entity | `understanding.entities` | YES | NO |
| | Quantity, Date, Ref | Scalar | `understanding.conditions` | NO | YES |
| **2. Purchase Return** | SKU, Warehouse | Entity | `understanding.entities` | YES | NO |
| | Quantity, Date, Ref | Scalar | `understanding.conditions` | NO | YES |
| **3. Transformation**| Source/Dest SKUs, WH | Entity | `understanding.entities` | YES | NO |
| | Quantities | Scalar | `understanding.conditions` | NO | YES |
| **4. Job Work Issue** | SKU, WH, Vendor | Entity | `understanding.entities` | YES | NO |
| | Quantity, Date | Scalar | `understanding.conditions` | NO | YES |
| **5. Job Work Return** | SKU, WH, Vendor | Entity | `understanding.entities` | YES | NO |
| | Quantity, Date | Scalar | `understanding.conditions` | NO | YES |
| **6. Exception Res** | Exception ID | Entity | `understanding.entities` | YES | NO |
| | Resolution Action | Scalar | `understanding.attributes` | NO | YES |
| **7. Stock Adjust** | SKU, Warehouse | Entity | `understanding.entities` | YES | NO |
| | Quantity, Reason | Scalar | `understanding.conditions` | NO | YES |

## 7. Missing Fields / Gaps
The `AbstractEvidenceRequest` lacks a strictly typed `ActionParameters` or `NormalizedScalars` object. Without this, the contract delivers unstructured semantic text rather than actionable parameter primitives (e.g., Dates, Decimals, Booleans).

## 8. R-7 Boundary Implications
If implemented immediately, R-7 would be forced to invent semantic interpretation:
- It would have to parse natural language quantities.
- It would have to parse relative dates ("tomorrow").
- It would perform conversational reasoning to distinguish a "reference number" from a "quantity" if the ID's intent extraction was sloppy.
This constitutes a massive boundary violation. R-7 MUST NOT perform these actions.

## 9. R-7 Implementation Readiness
**BLOCKED**
The upstream semantic contract must be extended before R-7 can be correctly implemented.

## 10. Exact Next Step
Extend the `AbstractEvidenceRequest` / `ConversationalUnderstanding` contract in `src/shared/` to explicitly support strictly-typed, normalized scalar action parameters (e.g., `ActionParameters` dictionary containing parsed primitives) before attempting any CEM-side R-7 adapter implementation.
