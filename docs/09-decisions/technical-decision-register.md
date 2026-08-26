# Technical Decision Register

## Purpose
This register tracks low-level, implementation-specific technical decisions that must be resolved prior to development (Milestone 0). These decisions dictate physical infrastructure, code patterns, and technology selections without altering the overarching AaramBooks architecture or domain boundaries.

---

## TDR-001: Backend Architecture Pattern
- **Status:** [CLOSED]
- **Options Considered:**
  - *Option A: Monorepo with separated modules.* All Intelligence Domains and Brain Core live in one repository but remain strictly decoupled via internal code interfaces.
  - *Option B: Polyrepo microservices.* Each Intelligence Domain and Brain Core gets its own repository and is deployed as an independent network service.
- **Recommendation:** Option A (Monorepo with separated modules).
- **Trade-offs:** A monorepo reduces CI/CD overhead and simplifies cross-module interface testing for the initial MVP. Polyrepo forces strict physical network boundaries but adds significant DevOps and deployment complexity for Milestone 0.
- **Final Decision:** Monorepo with separated modules.
- **Final Rationale:** Prioritizing velocity and simplified CI/CD for MVP-1. We will enforce logical decoupling via directory structure and interface boundaries rather than physical network boundaries.

---

## TDR-002: Database Strategy (Memory Framework)
- **Status:** [DEFERRED]
- **Options Considered:**
  - *Option A: PostgreSQL with pgvector.* A unified relational database that handles both structured session state and vector embeddings.
  - *Option B: Polyglot persistence (Redis + Pinecone/Weaviate).* Redis for fast transient session state; a dedicated vector database for knowledge embeddings and semantic memory.
  - *Option C: Managed Database-as-a-Service.* Using a fully managed third-party vector/NoSQL database provider.
- **Recommendation:** Defer to implementation phase.
- **Trade-offs:** Locking in a database now violates the Build-vs-Buy strategy. Aaram must own the logical memory semantics and abstractions, not necessarily the physical storage technology.
- **Final Decision:** Deferred to Implementation Phase.
- **Final Rationale:** Under the Build-vs-Buy strategy, vector and database infrastructure are commodity components (BUY/USE). The exact physical storage technology will be selected during implementation based on available managed services, ensuring it remains behind the Aaram-owned Memory Framework abstraction.

---

## TDR-003: Internal Communication Protocol
- **Status:** [CLOSED]
- **Options Considered:**
  - *Option A: REST/JSON over HTTP.* Standard, ubiquitous, and easy to debug.
  - *Option B: gRPC/Protobuf.* Strongly typed contracts, lower latency, and highly efficient serialization.
  - *Option C: Event-driven (Kafka/RabbitMQ).* Fully asynchronous pub/sub.
- **Recommendation:** Option B (gRPC).
- **Trade-offs:** gRPC enforces strict, code-generated API contracts (via Protobuf) between Intelligence Domains and Brain Core, naturally aligning with the API Contract Boundary rules. REST is easier to test manually but lacks native strict contract enforcement. Event-driven architecture adds unnecessary latency for synchronous conversational responses.
- **Final Decision:** REST/OpenAPI for MVP, gRPC deferred if required.
- **Final Rationale:** While gRPC provides strict contracts, REST/OpenAPI is faster to bootstrap and debug during MVP-1. We will enforce contracts using OpenAPI schemas rather than Protobuf initially. gRPC adoption is deferred until performance or strict binary contracts become an absolute necessity.

---

## TDR-004: AI Provider Strategy (Model Gateway)
- **Status:** [CLOSED]
- **Options Considered:**
  - *Option A: Single Provider (e.g., OpenAI API).* Use GPT-4o for all reasoning, intent parsing, and conversation generation.
  - *Option B: Multi-Provider / Agnostic (e.g., LiteLLM adapter).* Abstract API calls through a router that can dynamically switch between OpenAI, Anthropic, and open-source models.
- **Recommendation:** Option B (Use an off-the-shelf Multi-Provider Gateway).
- **Trade-offs:** Option B prevents vendor lock-in, fulfilling the core mandate of the Model Gateway. Building a custom gateway from scratch violates the Build-vs-Buy strategy. Option A is faster to implement initially but risks tight coupling to one vendor's API design.
- **Final Decision:** Integrate an off-the-shelf multi-provider Model Gateway.
- **Final Rationale:** Vendor independence is a hard architectural rule. To prevent vendor lock-in without reinventing the wheel, we will BUY/USE an off-the-shelf commodity model gateway (e.g., LiteLLM or similar) rather than implementing a custom routing infrastructure from scratch. Aaram owns the interface abstraction, not the gateway infrastructure.

---

## TDR-005: Deployment Architecture
- **Status:** [CLOSED]
- **Options Considered:**
  - *Option A: Serverless Functions (AWS Lambda / Google Cloud Functions).* Highly scalable, zero maintenance for idle time.
  - *Option B: Containerized Orchestration (Docker / Kubernetes / ECS).* Long-running containers managing continuous state.
- **Recommendation:** Option B (Containerized Orchestration).
- **Trade-offs:** AI reasoning and memory context assembly often suffer from severe serverless cold starts. Long-running containers provide predictable latency for continuous conversational intelligence, although they require more active infrastructure management.
- **Final Decision:** Containerized deployment using Docker-based approach. Kubernetes deferred.
- **Final Rationale:** Containerization solves the cold-start latency problem for conversational AI, but full Kubernetes orchestration is too heavy for MVP-1. A simple Docker-based deployment provides the necessary environment consistency without the operational overhead of K8s.
