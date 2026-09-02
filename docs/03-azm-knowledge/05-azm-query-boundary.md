# Azm Query Boundary

**Document Reference:** `docs/03-azm-knowledge/05-azm-query-boundary.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. The Authoritative Access Boundary

The flow of semantic and schematic knowledge to Aaram's AI capabilities is strictly governed by the following invariants:

**INTENDED:** `BRAIN → AZM → KNOWLEDGE`
**FORBIDDEN:** `BRAIN → BUSINESS SYSTEM PUBLIC CONTRACT`
**FORBIDDEN:** `BRAIN → BUSINESS SYSTEM DATABASE` (for meaning)
**FORBIDDEN:** `INTELLIGENCE DOMAIN → BUSINESS SYSTEM PUBLIC CONTRACT` (to reconstruct semantics)

Brain Core is entirely blind to the meaning of the ecosystem without Azm. It cannot bypass Azm to read a markdown file or reverse-engineer a DDL script.

Intelligence Domains are equally prohibited from directly reading BS Public Contracts to understand meaning. An Intelligence Domain that reads BS contracts directly has become a shadow semantic master — which violates the 4-box architecture.

---

## 2. AZM Is Not Brain

This distinction is an architectural invariant:

- **AZM** prepares and maintains persistent knowledge: it normalizes contract declarations and performs **limited, governed knowledge derivation at ingestion time**.
- **Brain Core** reasons over that knowledge at query time: it interprets user intent, selects relevant concepts, and determines how an operational query should be formed.

AZM does NOT perform runtime reasoning or inference. It answers knowledge queries from its persistent store. Brain Core reasons.

---

## 3. Knowledge Retrieval vs. Operational Retrieval

The architecture makes a rigorous distinction between asking for knowledge and asking for operational data.

### 3.1 What Brain Asks Azm (Knowledge Retrieval)
Brain is permitted to request:
- *"What is a SKU?"* (Concept Resolution).
- *"Which Business System owns SKU?"* (Provenance).
- *"What concepts relate to SKU?"* (Relational Navigation).
- *"Which field in this schema maps to the 'Selling Price' concept?"* (Schematic Retrieval).
- *"Is this mapping active or deprecated?"* (State).

### 3.2 What Brain NEVER Asks Azm (Operational Retrieval)
Azm must not persist current transactional records merely to make querying convenient. Azm DOES NOT answer:
- *"What is SKU 126BS's current stock?"*
- *"What is today's order count?"*
- *"What is the current selling price of record X?"*

---

## 4. The Execution Handoff

Azm provides **Knowledge**. Brain Core (and its Execution Machinery) accesses **Operational Reality** separately.

```
Brain asks Azm:         "Where is Inventory data?"
Azm replies:            "It is governed by Inventory BS,
                         exposed via vw_stock_balances,
                         field 'on_hand_quantity' maps to concept inventory.stock_balance."

Brain uses Execution Machinery to execute:
                         SELECT on_hand_quantity FROM vw_stock_balances WHERE sku = ?
```

Azm is out of the loop the moment actual operational data is queried. Azm's role ends when it answers the knowledge query.

---

## 5. Open Gaps

**OPEN GAP / DECISION REQUIRED:** The exact query API/protocol that Brain Core uses to query Azm (e.g., GraphQL, REST, direct Python interface) remains an open implementation design decision.
