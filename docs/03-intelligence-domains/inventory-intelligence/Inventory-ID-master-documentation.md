# Inventory Intelligence Domain Master Documentation

## IID-F1: Rich Semantic Operators — COMPLETED

### Supported Generic Operators
The Intent Parsing phase (IID-2) extracts and Brain Core supports the following generic operators without Inventory-specific knowledge:
- `EQUALS`
- `NOT_EQUALS`
- `GREATER_THAN`
- `GREATER_THAN_OR_EQUAL`
- `LESS_THAN`
- `LESS_THAN_OR_EQUAL`
- `IN`
- `NOT_IN`
- `BETWEEN`

### Extraction Model
The Inventory Intelligence Orchestrator (cognitive LLM) parses explicit user queries (e.g. "Stock below 50") into `SemanticConstraint` structures that explicitly tag the `operator` field.

### Validation Rules
The orchestrator validates all extracted operators against a strict allowlist. Any unrecognized operator hallucinated by the LLM (e.g., `APPROXIMATELY`) results in immediate deterministic fallback and query rejection.

### Provenance Rules
The LLM does not hallucinate thresholds. Thresholds are only passed through if the user explicitly supplied them (e.g., "Consider low stock as < 50") or if Azm provided a certified policy. User-supplied criteria retain `USER_SUPPLIED` provenance metadata all the way through generic execution and final memory retention.

### Downstream Execution Verification
The `SemanticConstraint` model natively supports these string operators, allowing the `ContextCapabilityGateway` to seamlessly transmit rich constraint logic to downstream CEM/providers via JSON payload, requiring no semantic understanding in Brain Core itself.

### Testing
- Fully validated via `test_rich_operators.py` and operator contract testing.
- Full regression (110 tests) maintained 100% pass rate.

### Architectural Statement
**CRITICAL:** No Inventory business thresholds (e.g., low-stock triggers, aging rules, reorder limits) have been hardcoded into Brain Core or IID. The system remains fully reliant on dynamic explicit context from Azm or User Prompts.
