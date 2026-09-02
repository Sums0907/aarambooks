# Azm (Aaram Zameer): The Semantic & Schematic Repository

**Document Reference:** `docs/03-azm-knowledge/README.md`
**System Name:** Aaram Zameer (`Azm`)
**Domain Layer:** Central Knowledge Registry (Container 3)
**Classification:** Foundational Architecture & Boundary Grounding

---

## 1. The Soul of Azm

**Azm (عزم)** is an Urdu word meaning **resolve** and **determination**. It was designed with a very personal and deep connection to the Aaram ecosystem.

Azm is the **global persistent repository of the semantic and schematic knowledge** of the entire ecosystem. It does not just hold data; it derives and represents the *meaning* of the data across boundaries.

**Precise Definition:**
> AZM is AaramBooks' declarative semantic-and-schematic knowledge layer: it owns the persistent representation of ecosystem knowledge, normalizing what business concepts mean, how they relate across systems, and what governed public schemas expose them.

It explicitly **DOES NOT** own:
- canonical operational business truth
- operational business records
- transactional state
- business workflow execution
- runtime context extraction
- business-rule enforcement

---

## 2. The Cognitive Split: The 4-Box Separation of Concerns

The ecosystem is strictly divided into four distinct components:

| Box | The Core Responsibility | Example |
|---|---|---|
| **1. Business System (BS)** | **WHAT** is actually true and what may be changed? | *"SKU 126BS has 10 units in stock. Uniqueness constraints pass."* |
| **2. AZM** | **WHAT** does this concept mean and **WHAT** schema exposes it? | *"A 'SKU' is a stock-keeping unit. It is exposed via `vw_stock_balances`."* |
| **3. Brain Core** | **HOW** do we resolve/interpret the user's requirement? | *"The user's query translates to a SQL `SELECT` intent against `vw_stock_balances`."* |
| **4. Intelligence Domain** | **WHAT** does this mean for this particular business objective? | *"Given the inventory balances, this SKU represents a low-stock risk for the customer's query."* |

---

## 3. Exactly Two Public Contracts: Equilibrium & Decoupling

To ensure perfect decoupling, Business Systems (BS) publish **exactly two governed contracts**:

1. **Semantic Public Contract:** WHAT the business concepts mean, domain terminology, and semantic boundaries (authored/governed by the BS).
2. **Schematic Public Contract:** HOW those concepts are exposed/accessed via public views, APIs, or MCP schemas (authored/governed by the BS).

**AZM consumes and curates ONLY these two contracts.** It transforms these governed declarations into a unified persistent knowledge model. Operational records remain strictly inside the Business System.

---

## 4. Cross-Business-System Knowledge Integration

A primary architectural purpose of Azm is representing relationships *across* Business Systems. It is not merely a mirror of individual BS schemas. 

For example, Azm represents ecosystem-level knowledge such as:
- **SKU** (Catalog BS concept) 
  - *has* **Stock Balance** (Inventory BS concept)
  - *appears in* **Order Line** (Order BS concept)

This unified ontology is what allows Brain Core to orchestrate multi-domain workflows seamlessly.

---

## 5. Architectural Evolution (The Roadmap)

Azm is an independent, persistent system on a clear evolutionary path.

- **Phase 1 (Legacy Bootstrap):** Azm defined declaratively in Python scripts (`src/azm/namespaces/`).
- **Phase 2 (Persistent Ingestion):** Azm becomes a dynamic, persistent knowledge database that ingests the two Public Contracts from all Business Systems.
- **Phase 3 (FUTURE RESEARCH / LONG-TERM POSSIBILITY):** Azm serves as the foundational training data generator to fine-tune a local LLM. A potential long-term possibility is that the LLM absorbs the knowledge so deeply that a distinct Azm database becomes unnecessary. However, the persistent Azm architecture must remain valid regardless of LLM strategy shifts.

---

## 6. Namespaces (Federated Knowledge)

Azm logically partitions its knowledge into domain namespaces, derived from the owning Business Systems:

- **Inventory** (Derived from Inventory BS Contracts)
- **NDR (Logistics)** (Derived from Order/Logistics BS Contracts)
- **ShopDeck** (Classified strictly as External/Channel Knowledge)
- **Catalog** (Derived strictly from Aaram Catalog BS Contracts)
