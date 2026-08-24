# AG Architecture Onboarding Report

## 1. Understanding of the Ecosystem

AaramBooks is an AI-native business operating system designed around a fundamental separation of concerns: operational execution versus intelligence generation. 

The ecosystem is strictly governed by the core principle:
> **"Business systems create truth. Aaram Brain creates intelligence from that truth."**

This ensures that AaramBooks avoids the common pitfall of monolithic AI platforms. Instead, it maintains highly cohesive, loosely coupled business domains that interact with a centralized, domain-neutral intelligence layer. Information flows securely between these systems via well-defined API contracts and events without ever transferring ownership of the underlying business truth.

---

## 2. Current Architecture Summary

The AaramBooks ecosystem is structured into a hierarchical, three-layer architecture:

1. **Business Domain Systems Layer:** The foundational operational layer. These systems execute deterministic business processes, maintain compliance, and serve as the single source of truth for all operational records.
2. **Aaram Brain Core Layer:** The centralized intelligence foundation. It abstracts underlying AI models and provides reusable, generic intelligence capabilities (understanding, reasoning, memory, and decision support). 
3. **Intelligence Applications / Domains Layer:** The business-facing intelligence layer. These applications apply the generic capabilities of the Brain Core to solve specific, highly contextualized business challenges (e.g., resolving delivery issues or answering customer queries).

Communication across these boundaries is strictly controlled. API contracts expose capabilities, and events communicate business changes and collaboration signals—neither is permitted to create duplicate operational databases.

---

## 3. Domain Ownership Summary

Ownership within AaramBooks is defined by responsibility. A domain owns exactly what it is responsible for and nothing more.

- **AaramIdentity:** Owns the truth regarding who users are and what they are allowed to do. It handles identity, authentication, authorization, roles, and permissions.
- **AaramInventory:** Owns the truth regarding physical and digital stock. It handles product definitions, SKUs, inventory states, and stock movements.
- **AaramPacking:** Owns the truth regarding physical warehouse execution. It handles packing workflows and physical operational events.

*Crucially, Aaram Brain owns intelligence capabilities. It consumes operational truth from the above systems to generate insights, but it is strictly forbidden from owning or altering that operational truth.*

---

## 4. Brain Core Understanding

Aaram Brain Core is the intelligence engine that powers the ecosystem. It is domain-neutral and reusable. It consists of the following independent engines and frameworks:

- **Context Engine:** Understands the "who, what, where, and when" of a business situation.
- **Knowledge Engine:** Maintains ecosystem understanding, business rules, concepts, and organizational policies.
- **Reasoning Engine:** Analyzes patterns, relationships, and situations based on context and knowledge.
- **Decision Engine:** Evaluates alternatives and provides actionable recommendations.
- **Action Engine:** Connects intelligence outcomes to controlled business execution workflows.
- **Memory Framework:** Defines how intelligence (long-term, interaction, and experience memory) is retained without duplicating business databases.
- **Model Gateway:** Abstract boundary between Brain Core capabilities and external AI providers (e.g., LLMs), ensuring architectural independence from specific technologies.

---

## 5. Potential Implementation Risks & Missing Decisions

While the conceptual architecture (Modules 00-10) is robust and approved, as we transition to implementation, several risks and missing physical decisions must be addressed:

1. **Infrastructure & Integration Technology:** 
   The event architecture and API contracts are conceptually defined, but the physical implementations (e.g., Kafka, gRPC, REST, GraphQL, Webhooks) are currently undecided. This could lead to divergent implementation patterns if not standardized early.
2. **Latency & Caching vs. Duplicate Truth:** 
   Because Aaram Brain relies entirely on business systems for operational truth, high-latency queries could degrade intelligence response times. Caching strategies will be necessary but must be carefully governed to avoid accidentally creating "duplicate operational databases," which would violate core rules.
3. **Fallback & Business Continuity:** 
   A clear strategy is needed to define how Business Domain Systems operate if the Model Gateway or underlying AI providers experience outages. Operational systems must remain fully functional and independent of intelligence latency or downtime.
4. **Data Model Translation:**
   Defining exactly how Business Data Models are mapped to Intelligence Context Models (and ensuring changes in business models don't tightly couple to and break Brain Core reasoning) will require strict anti-corruption layers.
