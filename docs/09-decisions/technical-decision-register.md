# Technical Decision Register

## Purpose
This register tracks low-level, implementation-specific technical decisions that must be resolved prior to development (Milestone 0). These decisions dictate physical infrastructure, code patterns, and technology selections without altering the overarching AaramBooks architecture or domain boundaries.

---

## TDR-001: Backend Architecture Pattern
- **Status:** [OPEN]
- **Options Considered:**
  - *Option A: Monorepo with separated modules.* All Intelligence Domains and Brain Core live in one repository but remain strictly decoupled via internal code interfaces.
  - *Option B: Polyrepo microservices.* Each Intelligence Domain and Brain Core gets its own repository and is deployed as an independent network service.
- **Recommendation:** Option A (Monorepo with separated modules).
- **Trade-offs:** A monorepo reduces CI/CD overhead and simplifies cross-module interface testing for the initial MVP. Polyrepo forces strict physical network boundaries but adds significant DevOps and deployment complexity for Milestone 0.
- **Final Decision:** [OPEN]

---

## TDR-002: Database Strategy (Memory Framework)
- **Status:** [OPEN]
- **Options Considered:**
  - *Option A: PostgreSQL with pgvector.* A unified relational database that handles both structured session state and vector embeddings.
  - *Option B: Polyglot persistence (Redis + Pinecone/Weaviate).* Redis for fast transient session state; a dedicated vector database for knowledge embeddings and semantic memory.
- **Recommendation:** Option A (PostgreSQL with pgvector).
- **Trade-offs:** Option A provides operational simplicity and reduces the number of moving parts during MVP-1. Option B provides specialized performance at scale but introduces infrastructure fragmentation and complex data synchronization.
- **Final Decision:** [OPEN]

---

## TDR-003: Internal Communication Protocol
- **Status:** [OPEN]
- **Options Considered:**
  - *Option A: REST/JSON over HTTP.* Standard, ubiquitous, and easy to debug.
  - *Option B: gRPC/Protobuf.* Strongly typed contracts, lower latency, and highly efficient serialization.
  - *Option C: Event-driven (Kafka/RabbitMQ).* Fully asynchronous pub/sub.
- **Recommendation:** Option B (gRPC).
- **Trade-offs:** gRPC enforces strict, code-generated API contracts (via Protobuf) between Intelligence Domains and Brain Core, naturally aligning with the API Contract Boundary rules. REST is easier to test manually but lacks native strict contract enforcement. Event-driven architecture adds unnecessary latency for synchronous conversational responses.
- **Final Decision:** [OPEN]

---

## TDR-004: AI Provider Strategy (Model Gateway)
- **Status:** [OPEN]
- **Options Considered:**
  - *Option A: Single Provider (e.g., OpenAI API).* Use GPT-4o for all reasoning, intent parsing, and conversation generation.
  - *Option B: Multi-Provider / Agnostic (e.g., LiteLLM adapter).* Abstract API calls through a router that can dynamically switch between OpenAI, Anthropic, and open-source models.
- **Recommendation:** Option B (Multi-Provider adapter).
- **Trade-offs:** Option B requires slightly more setup but prevents vendor lock-in, fulfilling the core mandate of the Model Gateway. Option A is faster to implement initially but risks tight coupling to one vendor's prompt structure and API design.
- **Final Decision:** [OPEN]

---

## TDR-005: Deployment Architecture
- **Status:** [OPEN]
- **Options Considered:**
  - *Option A: Serverless Functions (AWS Lambda / Google Cloud Functions).* Highly scalable, zero maintenance for idle time.
  - *Option B: Containerized Orchestration (Docker / Kubernetes / ECS).* Long-running containers managing continuous state.
- **Recommendation:** Option B (Containerized Orchestration).
- **Trade-offs:** AI reasoning and memory context assembly often suffer from severe serverless cold starts. Long-running containers provide predictable latency for continuous conversational intelligence, although they require more active infrastructure management.
- **Final Decision:** [OPEN]
