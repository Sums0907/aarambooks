# Azm Query Boundary

**Document Reference:** `docs/03-azm-knowledge/05-azm-query-boundary.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. The Authoritative Access Boundary

The flow of semantic and schematic knowledge to Aaram's AI capabilities is strictly governed by the following invariant:

**INTENDED:** `BRAIN → AZM → KNOWLEDGE`
**FORBIDDEN:** `BRAIN → BUSINESS SYSTEM PUBLIC CONTRACT`
**FORBIDDEN:** `BRAIN → BUSINESS SYSTEM DATABASE` (for meaning)

Brain Core is entirely blind to the meaning of the ecosystem without Azm. It cannot bypass Azm to read a markdown file or reverse-engineer a DDL script.

---

## 2. Knowledge Retrieval vs. Operational Retrieval

The architecture makes a rigorous distinction between asking for knowledge and asking for operational data.

### 2.1 What Brain Asks Azm (Knowledge Retrieval)
Brain is permitted to request:
- *"What is a SKU?"* (Concept Resolution).
- *"Which Business System owns SKU?"* (Provenance).
- *"What concepts relate to SKU?"* (Relational Navigation).
- *"Which field in this schema maps to the 'Selling Price' concept?"* (Schematic Retrieval).
- *"Is this mapping active or deprecated?"* (State).

### 2.2 What Brain NEVER Asks Azm (Operational Retrieval)
Azm must not persist current transactional records merely to make querying convenient. Azm DOES NOT answer:
- *"What is SKU 126BS's current stock?"*
- *"What is today's order count?"*
- *"What is the current selling price of record X?"*

---

## 3. The Execution Handoff

Azm provides **Knowledge**. Brain Core (and its Execution Machinery) accesses **Operational Reality**.

1. Brain asks Azm: *"Where is Inventory data?"*
2. Azm replies: *"It is governed by the Inventory BS, exposed via `vw_stock_balances`."*
3. Brain uses authorized Business System access mechanisms (Execution Machinery) to execute a query against `vw_stock_balances`.

Azm is out of the loop the moment actual operational data is queried.

**OPEN GAP / DECISION REQUIRED:** The exact query API/protocol that Brain Core uses to query Azm (e.g., GraphQL, REST, direct Python interface) remains an open implementation design decision.
