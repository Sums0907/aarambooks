# Azm (Aaram Zameer): The Semantic & Schematic Repository

**Document Reference:** `docs/03-azm-knowledge/README.md`
**System Name:** Aaram Zameer (`Azm`)
**Domain Layer:** Central Knowledge Registry (Container 3)
**Classification:** Foundational Architecture & Boundary Grounding

---

## 1. The Soul of Azm

**Azm (عزم)** is an Urdu word meaning **resolve** and **determination**. It was designed with a very personal and deep connection to the Aaram ecosystem.

Azm is the **global repository of the semantic and schematic knowledge** of the entire ecosystem. It does not just hold data; it holds the *meaning* of the data. 

**Precise Definition:**
> AZM is AaramBooks' declarative semantic-and-schematic knowledge layer: it defines what business concepts mean, how they are named and related, and what governed public schemas/views expose those concepts to intelligence capabilities.

It explicitly **DOES NOT** own:
- operational business records
- transactional state
- business workflow execution
- runtime context extraction
- business-rule enforcement

---

## 2. The Cognitive Split: The 4-Box Separation of Concerns

To prevent future agents from losing the context of where Azm sits in the ecosystem, the boundaries between the layers are defined by this precise questioning framework:

| Layer | The Core Responsibility | Example |
|---|---|---|
| **AZM** | **WHAT** does this concept mean? <br> **WHAT** schema exposes it? | *"A 'SKU' is a stock-keeping unit. It is exposed via `vw_stock_balances`."* |
| **Brain Core** | **HOW** do we resolve/interpret the user's requirement? | *"The user's query translates to a SQL `SELECT` intent against `vw_stock_balances`."* |
| **Intelligence Domain** (e.g., Catalog ID) | **WHAT** does this mean for this particular business objective? | *"Given the inventory balances, this SKU represents a low-stock risk for the customer's query."* |
| **Business System** (e.g., Catalog BS) | **WHAT** is actually true and what may be changed? | *"SKU 126BS has 10 units in stock. Uniqueness constraints pass."* |

---

## 3. The Equilibrium of Semantic & Schematic Knowledge

Historically, to enforce strict decoupling, Azm contained *only* Semantic Knowledge, while Schematic Knowledge was locked inside the Business Systems (BS). However, this left Brain Core fundamentally blind ("dumb") to the structure of the data it needed to reason over.

The architectural equilibrium achieved is the **Semantic and Schematic Public Read Contract**:
1. The Business System (BS) exposes and maintains Public Read Contracts (SQL Views, MCP schemas). 
2. Azm periodically syncs and reads these contracts, pulling them into its knowledge repository. 
3. This allows the BS to safely change schemas at will, while Azm gracefully stays updated as the ecosystem's brain map.

---

## 4. Architectural Evolution & The LLM Endgame (The Roadmap)

Azm is a bridge to a much larger vision. 

- **Phase 1 (Current):** Azm is defined declaratively in Python scripts (`src/azm/namespaces/`).
- **Phase 2 (Persistent Sync):** Azm becomes a dynamic, persistent repository that automatically syncs Semantic and Schematic Public Read Contracts from the BS.
- **Phase 3 (The Training Flywheel):** Azm serves as the foundational training data generator. As human operators interact with Brain Core, their queries and Azm's structured responses are collected to fine-tune a local, open-source LLM (e.g., Qwen).
- **Phase 4 (The Ultimate Endgame):** The local LLM model absorbs the Aaram ecosystem's knowledge so deeply into its own neural weights that Azm is eventually rendered obsolete. The long-term vision is to **completely dissolve Azm, making its semantic and schematic knowledge an integral, native part of the local LLM itself.**

---

## 5. Namespaces (Federated Knowledge)

Azm is explicitly organized as an ecosystem-wide knowledge registry, partitioned into domain namespaces.

- **Inventory** (`src/azm/namespaces/inventory.py`)
- **NDR (Logistics)** (`src/azm/namespaces/ndr.py`)
- **ShopDeck** (`src/azm/namespaces/shopdeck.py`)

*(Note: The Catalog namespace is currently an identified architectural gap to be addressed).*
