---
source_bs: "catalog"
namespace_name: "catalog"
namespace_classification: "AARAM_NATIVE"
namespace_description: "Aaram Catalog Business System — commercial product and SKU knowledge"
contract_version: "1.0"
---

# Aaram Catalog Semantic Public Contract

**Document Reference:** `business_systems/catalog/public-contracts/catalog-semantic-public-contract.md`
**System Name:** Sovereign Catalog Business System (`Catalog BS`)
**Status:** Certified Core Semantic Public Contract
**Last Updated:** September 2026

---

## 1. Purpose, Scope & Authority
This document defines the **Canonical Semantic Public Contract** for the Aaram Catalog Business System.
It answers exclusively: **What does an Aaram Catalog concept mean?**

## 2. Aaram Catalog Ontology & Core Concept Definitions

### Concept: Product
- **Semantic Key:** catalog.entity.product
- **Concept Type:** ENTITY
- **Definition:** A commercial grouping or design family under which one or more sellable SKUs are presented to customers as a single offering.
- **Aliases:** product, product family, commercial family, parent

### Concept: SKU
- **Semantic Key:** catalog.entity.sku
- **Concept Type:** ENTITY
- **Definition:** The discrete, sellable, physical unit that is priced, packed, and shipped. The atomic operational unit of commerce.
- **Aliases:** sku, sellable unit, variant, child, product variant

---

## 3. Relationships

### Relationships

| Source Key | Target Key | Type | Derivation Rule | Source Element |
|---|---|---|---|---|
| catalog.entity.product | catalog.entity.sku | CONTAINS | catalog_2tier_containment | Section 2 — 2-Tier Model (Product=Parent, SKU=Child) |

---

## 4. Identity Semantics & External Mappings
Aaram enforces a multi-tier identity model. External channel identifiers are strictly mapped, never adopted as core identity.

### External Mappings

| Native Concept | External System | External Key | Display Name |
|---|---|---|---|
| catalog.entity.sku | shopdeck | customer_sku_short_id | ShopDeck customer_sku_short_id |
| catalog.entity.product | shopdeck | customer_product_short_id | ShopDeck customer_product_short_id |

---

## 8. Open Gaps & Decisions Required
- **OPEN GAP (Pricing Limits):** Is `selling_price < cost_price` treated as a hard blocking invariant in Catalog BS, or just a warning alert? Currently provisional.
