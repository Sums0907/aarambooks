# Cognitive Planning Contracts

This document formalizes the fundamental data contracts that govern the interaction between the Cognitive Planner, the Brain Orchestrator, the Context/Evidence Engine, and Intelligence Domains.

These contracts are conceptually generic and decoupled from any specific domain (e.g., Inventory) or physical transport layer (e.g., REST, SQL). They define the architectural boundary between determining *what* evidence is needed and *how* it is retrieved.

## 1. EvidencePlan
Represents what evidence the cognitive planning process determines is required to answer a user's request. It strictly expresses *what* is needed, not *how* it is physically retrieved.

- **plan_id**: Unique identifier for the plan.
- **original_intent**: The interpreted objective of the user's natural language query.
- **domain_context**: The broad domain area (e.g., `inventory`, `ndr`).
- **requirements**: List of `EvidenceRequirement` objects.
- **planning_dependencies**: Execution ordering or dependencies among requirements.
- **metadata**: High-level semantic constraints or ambiguities.

## 2. EvidenceRequirement
Represents an individual evidence requirement within an `EvidencePlan`.

- **requirement_id**: Unique identifier.
- **semantic_description**: Description of the required business evidence (e.g., "Current stock levels for SKU-123").
- **necessity**: Priority level (`CRITICAL`, `SUPPORTING`, `OPTIONAL`).
- **time_range**: Optional temporal constraints (e.g., "Past 30 days").
- **filters**: Semantic constraints (e.g., "Only overstocked items").
- **preferred_capability**: Optional hint of a known Context Capability that might fulfill this requirement.
- **rationale**: Why this evidence is needed for the original intent.

## 3. EvidencePlanExtension
Defines how the planning process requests additional evidence after reviewing an insufficient `EvidencePackage`.

- **parent_plan_id**: Reference to the original `EvidencePlan`.
- **extension_id**: Unique identifier for the extension.
- **new_requirements**: List of additional `EvidenceRequirement` objects.
- **reason_for_extension**: Semantic rationale for the iterative loop (e.g., "Initial jobwork analysis revealed vendor X has high leakage, now require historical scraps for vendor X").

## 4. ContextAssemblyRequest
Defines the deterministic execution request sent from the Brain Orchestrator into the Context/Evidence Engine.

- **request_id**: Unique identifier.
- **evidence_requirement**: The specific `EvidenceRequirement` being requested.
- **resolution_strategy**: Instructions from the Orchestrator (e.g., `USE_CAPABILITY`, `DYNAMIC_DISCOVERY`).
- **authorization_context**: Verified identity and permissions (e.g., `AARAM_BRAIN_APP`).
- **execution_constraints**: Timeouts, maximum payload sizes, or specific tenant isolations.

## 5. EvidencePackage
Defines the normalized evidence returned to the reasoning layer.

- **package_id**: Unique identifier.
- **plan_id**: Reference to the `EvidencePlan`.
- **evidence_items**: List of `EvidenceItem` objects containing the retrieved data.
- **sufficiency_assessment**: High-level assessment (`SUFFICIENT`, `PARTIAL`, `INSUFFICIENT`).
- **gaps**: List of missing evidence requirements and their corresponding `GapSemantics`.

## 6. EvidenceItem & Provenance Metadata
Formalizes the minimum metadata required to establish where a fact came from and whether it can safely be relied upon.

- **item_id**: Unique identifier for the fact/dataset.
- **semantic_identity**: What this data represents (e.g., `INVENTORY_MOVEMENT_LEDGER`).
- **data_payload**: The normalized factual data structure.
- **provenance**:
  - **source_system**: The authoritative business system (e.g., `AaramInventory`).
  - **retrieval_timestamp**: When Brain Core retrieved the data.
  - **business_timestamp**: The effective operational time of the data.
  - **derivation_metadata**: Indicates if the data is raw or aggregated/derived by the Context Engine.
- **confidence_quality**: Optional indicators of data completeness.

## 7. CapabilityResolutionResult
Represents how the Brain Orchestrator resolved an `EvidenceRequirement` to a retrieval mechanism.

- **requirement_id**: Reference to the requested evidence.
- **status**: The resolution outcome:
  - `EXACT_MATCH_CAPABILITY`: A predefined Context Capability exists.
  - `DYNAMIC_DISCOVERY_REQUIRED`: No predefined capability exists; semantic discovery required.
  - `UNRESOLVABLE`: Brain lacks both predefined capability and necessary semantic knowledge to construct a query.
- **resolved_provider**: The specific `SourceSystem` or `ContextCapability` selected.

## 8. Evidence Sufficiency / Gap Semantics
Clearly distinguishes the reasons why evidence might be missing or incomplete. These must not be collapsed into a generic "cannot answer" state.

- `EVIDENCE_SUFFICIENT`: Evidence successfully retrieved and covers the requirement.
- `EVIDENCE_PARTIAL`: Evidence retrieved but missing certain requested constraints (e.g., partial time range).
- `CONTEXT_CAPABILITY_UNAVAILABLE`: No predefined capability exists (triggers dynamic discovery).
- `DATA_UNAVAILABLE`: The underlying business truth does not exist in the source system.
- `SEMANTIC_KNOWLEDGE_GAP`: Brain lacks the schema/semantic knowledge to perform dynamic discovery for this requirement.
- `DATA_INACCESSIBLE`: Truth exists, but access is unauthorized or technically blocked.
- `EVIDENCE_CONFLICT`: Conflicting truth retrieved from multiple sources.
