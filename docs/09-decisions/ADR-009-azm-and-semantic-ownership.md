# ADR 009: Azm and Semantic Ownership

## Context
AaramBooks Brain Core architecture has reached Phase 14, where the requirement to handle arbitrary natural-language inventory questions emerged. Previously, Brain Core relied on predefined Context Capabilities and basic Cognitive Planning. However, addressing arbitrary questions requires a formal distinction between how the system processes meaning and who owns that meaning.

Furthermore, we established the long-term goal of building a proprietary intelligence asset that can be used to fine-tune open-weight models (like Qwen) in the future, rather than relying exclusively on frontier models like Gemini indefinitely.

## Decision
We establish a strict architectural ownership model separating Infrastructure from Knowledge, and formalize "Azm" (عزم) as the proprietary intelligence asset.

### Key Architectural Invariant

- **Semantic Infrastructure** answers HOW meaning is resolved.
- **Semantic Knowledge** answers WHAT that meaning is in the Aaram ecosystem.

- **Context Infrastructure** answers HOW evidence is obtained and governed.
- **Context Capability** represents WHAT authoritative business truth a business system can provide.

### Canonical Ownership Model

| WHAT IT IS | OWNER |
| :--- | :--- |
| **Semantic Infrastructure** (Machinery for resolving meaning) | **Brain Core** |
| **Semantic Knowledge** (Aaram/domain meaning) | **Intelligence Domain / Azm** |
| **Context Infrastructure** (Machinery for obtaining/governing evidence) | **Brain Core** |
| **Context Capability** (Authoritative business-system ability to provide truth) | **Business System** |
| **Cognitive Infrastructure** (Machinery for orchestration/control) | **Brain Core** |
| **Operational Truth** (Business data and state) | **Business System** |
| **Domain Reasoning** (Calculations, synthesis, evaluation) | **Intelligence Domain** |
| **Azm** (Ecosystem-wide evolving proprietary intelligence asset) | **AaramBooks** |

1. **Semantic Infrastructure (Brain Core):** Generic machinery for processing, resolving, discovering, translating, and using semantic information. Brain Core owns *how* semantics are processed, resolving domain-provided semantic requirements into concepts, entities, relationships, states, attributes, parameters, and capabilities.
2. **Semantic Knowledge (Azm):** Ecosystem-wide knowledge defining what business terms, entities, relationships, states, workflows and concepts mean.
3. **Intelligence Domain Adapter:** `DomainSemanticKnowledge` is merely a runtime adapter that projects relevant Azm knowledge to Brain Core. The Intelligence Domain does NOT own or hardcode the dictionary.
3. **Context Infrastructure (Brain Core):** Generic machinery for planning, resolving, authorizing, retrieving, normalizing, combining and tracking evidence.
4. **Context Capabilities (Business Systems):** AaramInventory and other systems own the operational truth and expose capabilities to retrieve it.
5. **Cognitive Infrastructure (Brain Core):** Generic planning, orchestration, and reasoning machinery.
6. **Azm (AaramBooks Asset):** Evolving, ecosystem-wide intelligence asset storing reasoning patterns, human feedback, evaluation data, and historical examples. It accumulates semantic and domain knowledge across all Intelligence Domains for future model specialization.

## Consequences
- **Brain Core genericism is preserved:** Brain Core will not contain inventory-specific logic, databases, or API rules.
- **Azm asset accumulation:** The architecture is now explicitly designed to capture domain knowledge and reasoning patterns as a future training asset.
- **Arbitrary queries supported:** By splitting semantic infrastructure from knowledge, Brain Core can resolve unknown NL queries dynamically using domain-provided semantics.
- **Implementation Dependency:** A generic Semantic Infrastructure layer must translate unstructured `EvidenceRequirement` semantics into structured `SemanticConstraint`s (e.g., Entity, State) using Azm definitions, without ever generating physical API query parameters.
