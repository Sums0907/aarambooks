---
source_bs: "shopdeck"
namespace_name: "shopdeck"
namespace_classification: "EXTERNAL_CHANNEL"
namespace_description: "ShopDeck Business System"
contract_version: "1.0"
---

# ShopDeck Semantic Public Contract

**Document Reference:** `business_systems/shopdeck/public-contracts/shopdeck-semantic-public-contract.md`
**System Name:** ShopDeck Business System
**Classification:** `EXTERNAL_CHANNEL`
**Status:** Certified Core Semantic Public Contract
**Last Updated:** September 2026

---

## 1. Purpose, Scope & Authority

This document defines the **Canonical Semantic Public Contract** for the ShopDeck Business System. It answers exclusively: **What does a ShopDeck concept mean?**

This contract is the singular source of truth for ShopDeck semantics across the AaramBooks ecosystem. It is intended to be ingested by the **AZM (Aaram Zero-trust Map)** to build the ShopDeck knowledge boundaries.

---

## 2. Core Ontology & Concept Definitions

### Concept: Customer
- **Semantic Key:** shopdeck.entity.customer
- **Concept Type:** ENTITY
- **Definition:** A buyer identified uniquely by ShopDeck via `customer_id`.
- **Aliases:** customer

### Concept: Customer Contact
- **Semantic Key:** shopdeck.entity.customer_contact
- **Concept Type:** ENTITY
- **Definition:** The encrypted phone number associated with the customer. Decryption is governed by ShopDeck proxy logic.
- **Aliases:** 

### Concept: Delivery Destination
- **Semantic Key:** shopdeck.entity.delivery_destination
- **Concept Type:** ENTITY
- **Definition:** The geographical delivery target (city, state, pincode) supplied at checkout.
- **Aliases:** 

### Concept: Order
- **Semantic Key:** shopdeck.entity.order
- **Concept Type:** ENTITY
- **Definition:** A commercial transaction representing a checkout session that converted into a purchase, identified by `order_id`.
- **Aliases:** order

### Concept: Order Item
- **Semantic Key:** shopdeck.entity.order_item
- **Concept Type:** ENTITY
- **Definition:** A distinct line item within an order, representing a specific product variant and commercial quantity.
- **Aliases:** 

### Concept: Order Item SKU ID
- **Semantic Key:** shopdeck.entity.order_item.sku_id
- **Concept Type:** ATTRIBUTE
- **Definition:** The authoritative ShopDeck order-item SKU identity (maps to customer_sku_short_id).
- **Aliases:** sku_id

### Concept: Payment
- **Semantic Key:** shopdeck.entity.payment
- **Concept Type:** ENTITY
- **Definition:** The financial exchange associated with an order.
- **Aliases:** 

### Concept: Payment Mode
- **Semantic Key:** shopdeck.entity.payment.mode
- **Concept Type:** ATTRIBUTE
- **Definition:** The mode of payment for the order (e.g., prepaid, cod).
- **Aliases:** payment_mode

### Concept: Payment Status
- **Semantic Key:** shopdeck.entity.payment.status
- **Concept Type:** STATE
- **Definition:** The status of the payment.
- **Aliases:** 

### Concept: Order Gross Value
- **Semantic Key:** shopdeck.entity.order.gross_value
- **Concept Type:** ATTRIBUTE
- **Definition:** The total gross value of the order.
- **Aliases:** order_value, total_amount

### Concept: Order Quantity
- **Semantic Key:** shopdeck.entity.order_quantity
- **Concept Type:** ATTRIBUTE
- **Definition:** The number of units purchased. (Strictly commercial, distinct from physical inventory).
- **Aliases:** 

### Concept: Shipment
- **Semantic Key:** shopdeck.entity.shipment
- **Concept Type:** ENTITY
- **Definition:** The physical dispatch of an order/item, identified universally by an Air Waybill (`awb_no`) assigned by a `courier_partner`.
- **Aliases:** shipment

### Concept: Courier Partner
- **Semantic Key:** shopdeck.entity.shipment.carrier
- **Concept Type:** ENTITY
- **Definition:** The external courier carrying the shipment.
- **Aliases:** 

### Concept: Shipment State
- **Semantic Key:** shopdeck.entity.shipment.state
- **Concept Type:** STATE
- **Definition:** The state of the shipment.
- **Aliases:** 

### Concept: Delivery Exception Reason
- **Semantic Key:** shopdeck.event.delivery_exception.reason
- **Concept Type:** ATTRIBUTE
- **Definition:** An objective event reported by a courier indicating a failed delivery attempt. Characterized by a raw string (`latest_ndr_reason`).
- **Aliases:** latest_ndr_reason, reason

### Concept: NDR Count
- **Semantic Key:** shopdeck.metric.ndr_count
- **Concept Type:** AGGREGATION
- **Definition:** The raw integer count of observed delivery exceptions for a shipment.
- **Aliases:** ndr_count, attempt_count

### Concept: Outreach Action
- **Semantic Key:** shopdeck.action.outreach
- **Concept Type:** TEMPORAL
- **Definition:** An automated or manual communication (SMS, IVR) executed by ShopDeck systems in response to an event, recorded chronologically.
- **Aliases:** 

### Concept: Checkout Session
- **Semantic Key:** shopdeck.event.checkout_session
- **Concept Type:** TEMPORAL
- **Definition:** An analytical grouping of user events prior to purchase.
- **Aliases:** 

---

## 3. Relationships

### Relationships

| Source Key | Target Key | Type | Derivation Rule | Source Element |
|---|---|---|---|---|
| shopdeck.entity.order | shopdeck.entity.order_item | CONTAINS | order_containment | ShopDeck DB |

---

## 4. Identity & Cross-System Mappings

Because ShopDeck is an `EXTERNAL_CHANNEL`, its identifiers map to canonical `AARAM_NATIVE` concepts where proven.

### External Mappings

| Native Concept | External System | External Key | Display Name |
|---|---|---|---|
| catalog.entity.sku | shopdeck | customer_sku_short_id | ShopDeck customer_sku_short_id |
| catalog.entity.sku.short_id | shopdeck | shopdeck.entity.order_item.sku_id | ShopDeck order_item.sku_id |

---

## 5. Excluded Intelligence Boundaries

To preserve architectural purity, the following concepts are **EXPLICITLY EXCLUDED** from this contract as they belong to downstream Intelligence Domains (e.g., NDR-ID):
*   Mapping raw courier reasons (e.g., "door locked") to normalized intents (e.g., `CUSTOMER_UNAVAILABLE`).
*   Assigning priority scores, CX risk scores, or operational risk scores to NDR events.
*   Defining recovery strategies (e.g., "3 attempts triggers priority escalation").
*   Diagnosing fake attempts or buyer remorse.
*   Calculating freight savings or financial outcomes.
