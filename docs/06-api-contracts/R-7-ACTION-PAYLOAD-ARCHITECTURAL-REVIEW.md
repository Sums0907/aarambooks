# R-7 ACTION PAYLOAD ARCHITECTURAL REVIEW

**Workspace: AaramBrain**

## 1. Authoritative Data Flow (NL to R-7)
1. **User NL Request:** e.g., "Receive 50 units of SKU X today."
2. **R-1 (Conversational Understanding):** The Intelligence Domain (ID) parses intent, extracting entities (SKU X) and normalizing scalar parameters (quantity=50.0, date="2026-08-29").
3. **R-2 (Requirement Classification):** Brain Core classifies the necessity of both entities and parameters (e.g., marking quantity as MANDATORY).
4. **R-3 (Evidence Request Formulation):** Brain Core wraps the classified requirement into the `AbstractEvidenceRequest` contract.
5. **R-4 (CEM Business Discovery):** CEM determines if it can fulfill the request based on the semantic intent.
6. **R-5 (CEM Semantic Entity Resolution):** CEM translates fuzzy semantic entities (SKU X) into physical opaque UUIDs. (Scalar parameters bypass this step).
7. **R-6 (Bounded Refinement):** If R-5 returns ambiguity, Brain Core may formulate a second pass using the opaque UUIDs. The scalar parameters remain intact.
8. **R-7 (CEM Business Execution):** The CEM capability adapter combines the R-5 UUIDs and the R-1 normalized scalar parameters to construct strict domain DTOs and execute the state change.

## 2. Precise Distinction: Entities vs Scalars vs Raw NL
- **Semantic Entity Parameters:** Abstract references to physical database rows (e.g., "Warehouse X", "Blue Bedsheets"). These absolutely require R-5 resolution to become opaque UUIDs.
- **Normalized Scalar/Action Parameters:** Strictly typed primitive values (e.g., `50.0`, `True`, `"2026-08-29"`) representing magnitudes, dates, or boolean states. These bypass R-5 entirely. They are directly consumed by R-7 to populate DTOs.
- **Conversational/Raw Expressions:** Unparsed NLP strings (e.g., "50 units", "next Tuesday"). These must be completely resolved into Normalized Scalars by R-1/Brain Core. R-7 must NEVER receive or parse these.

## 3. Where Typed Action Parameters Belong Architecturally
They must reside in **`ConversationalUnderstanding`**. 
Since the Intelligence Domain (R-1) is responsible for interpreting the natural language, it must emit the parsed primitives as part of its structured output. Placing them in `ConversationalUnderstanding` ensures that Brain Core's R-2 classifier can evaluate their conversational necessity (MANDATORY/OPTIONAL) identically to how it classifies entities.

## 4. Is `NormalizedParameter` the Correct Abstraction?
Yes. Relying on the generic `SemanticCondition(value=Any)` is insufficient because it lacks strict type guarantees and conflates action payload data with search filters. An explicit `NormalizedParameter(data_type, value)` array cleanly segregates R-7 execution primitives from R-5 entity targets, enabling strict Pydantic validation across the integration boundary.

## 5 & 6. R-7 Capability Parameter Matrix

| Capability | Parameter | Semantic/Scalar | Canonical Type | Source Stage | R-5 Involved? | R-6 Refinable? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Goods Receipt** | Quantity | Scalar | Decimal | R-1 | NO | YES |
| | Posting Date | Scalar | Date/Datetime | R-1 | NO | YES |
| | Reference | Scalar | String | R-1 | NO | YES |
| **Purchase Return** | Quantity | Scalar | Decimal | R-1 | NO | YES |
| | Posting Date | Scalar | Date/Datetime | R-1 | NO | YES |
| | Reference | Scalar | String | R-1 | NO | YES |
| **Transformation** | Source/Dest Qty | Scalar | Decimal | R-1 | NO | YES |
| | Posting Date | Scalar | Date/Datetime | R-1 | NO | YES |
| **Job Work Issue** | Quantity | Scalar | Decimal | R-1 | NO | YES |
| | Posting Date | Scalar | Date/Datetime | R-1 | NO | YES |
| **Job Work Return**| Quantity | Scalar | Decimal | R-1 | NO | YES |
| | Posting Date | Scalar | Date/Datetime | R-1 | NO | YES |
| **Exception Res.** | Action/Decision| Scalar | String/Enum | R-1 | NO | YES |
| | Reason | Scalar | String | R-1 | NO | YES |
| **Stock Adjust** | Quantity | Scalar | Decimal | R-1 | NO | YES |
| | Direction/Type | Scalar | String | R-1 | NO | YES |

*Validation Responsibility:* Brain Core (R-3) validates primitive typing against the canonical type. R-7 (CEM) validates domain business logic (e.g., "is quantity > 0?").

## 7. Verifying Boundary Security
The `NormalizedParameter` abstraction explicitly enforces boundaries:
- **No R-7 NLP:** The `data_type` enum forces R-1 to cast values to primitives before transmission. R-7 receives a strict Decimal or Date.
- **No R-7 Entity Resolution on Scalars:** R-7 only runs R-5 on `entities`, skipping `parameters`.
- **No Guessing Missing Values:** If a parameter is absent, R-7 accurately reports `EXECUTION_LIMITATION`, forcing Brain Core to handle the gap.
- **No Boundary Leakage:** Brain Core remains schema-agnostic. It simply transmits the primitive values required by the semantic intent.

## 8. R-6 Bounded Refinement Compatibility
The `NormalizedParameter` structures are perfectly compatible with R-6. When R-6 constructs the second-pass `AbstractEvidenceRequest`, it copies the original `ClassifiedRequirement` (which contains the `NormalizedParameter` array). The typed primitives survive the loop with full type safety and semantic provenance intact. R-6 does not need to parse or modify them.

## 9. RABTA-CEM Public Contract Compatibility
Adding `parameters: List[NormalizedParameter]` to `ConversationalUnderstanding` is a **Shared Contract Extension**. Because it defaults to an empty list, it is 100% backward compatible with existing `RETRIEVE` queries and legacy Stage F implementations. It extends the public contract but does not break it.

## 10. Missing Architectural Decisions
- **Decision Needed:** Does the Intelligence Domain (R-1) currently possess the NLP tooling to reliably cast "next Tuesday" into a strict ISO-8601 Date? If R-1 fails to cast this, the request will fail Pydantic validation at the R-3 boundary before reaching R-7.

## 11. Concrete Recommended Contract Shape

```python
class ParameterDataType(str, Enum):
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"
    STRING = "STRING"

class NormalizedParameter(BaseModel):
    parameter_name: str
    data_type: ParameterDataType
    value: Any  # Validated dynamically against data_type
    original_expression: str

# Added to ConversationalUnderstanding:
# parameters: List[NormalizedParameter] = Field(default_factory=list)
```

**Example Payload: Goods Receipt**
```json
{
  "understanding": {
    "intent": "ACTION",
    "entities": [
      {"original_expression": "SKU X"},
      {"original_expression": "Warehouse Y"}
    ],
    "parameters": [
      {
        "parameter_name": "inventory.numeric.quantity",
        "data_type": "DECIMAL",
        "value": 50.0,
        "original_expression": "50 units"
      },
      {
        "parameter_name": "inventory.temporal.posting_date",
        "data_type": "DATE",
        "value": "2026-08-29",
        "original_expression": "today"
      }
    ]
  }
}
```

## 12. Final Verdict
**READY FOR IMPLEMENTATION**
The architectural boundaries are sound. The contract extension is minimal, strictly typed, and completely backward compatible. We may proceed to implement the `NormalizedParameter` contract in Brain Core.
