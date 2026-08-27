# AaramBooks Brain Core — ShopDeck MCP Initial Data Acquisition & Operational Projection

## 1. Purpose of This Document

This document explains what **AaramBooks Brain Core** is being built to do and, specifically, what data we need to obtain from the **ShopDeck MCP** as the initial operational database for the Brain.

This document is intended to be given to a **ChatGPT conversation that has direct access to the ShopDeck MCP server**.

That ChatGPT conversation should use the ShopDeck MCP's read-only capabilities to inspect the available schema and extract the data required by AaramBooks.

The objective is **not** to build intelligence inside the MCP chat.

The objective is:

> **Use ShopDeck as the source of operational truth and provide AaramBooks with a sufficiently complete, structured historical dataset from which Brain Core can begin operating.**

---

# 2. What We Are Building

AaramBooks is being developed as an intelligent business system for Aaram Homes.

At the center is **Brain Core**.

Brain Core will eventually be responsible for:

- understanding business context
- answering business questions
- reasoning over operational data
- identifying patterns
- supporting decision-making
- providing domain intelligence
- eventually coordinating intelligence workflows across multiple business domains

However:

> **Brain Core must not become the owner of operational truth.**

Operational truth continues to belong to the systems that actually execute the business.

For example:

```text
ShopDeck
   │
   │ operational truth
   │
   ▼
ShopDeck Operational Projection
   │
   ▼
Brain Core
   │
   ▼
Context
   │
   ▼
Intelligence
```

The Brain consumes operational information.

It does not redefine the underlying business transaction.

---

# 3. Why ShopDeck Is Critical

ShopDeck is currently the overwhelmingly dominant operational system for the business.

Approximately **99% of orders** are handled through ShopDeck.

ShopDeck also currently integrates with the logistics/courier systems used for those orders and therefore contains important logistics-related information for those orders.

Therefore ShopDeck provides the most important external operational context required by Brain Core.

Without access to ShopDeck data:

> **Brain Core has very little practical operational value for the current business.**

This is why obtaining the ShopDeck dataset is a priority.

---

# 4. ShopDeck Is the Primary Source

For the majority of the business:

```text
Customer
   ↓
Order
   ↓
Order Item
   ↓
Shipment / AWB
   ↓
Courier / Logistics
   ↓
Delivery / NDR / RTO
   ↓
Return
```

ShopDeck currently represents this operational chain.

The data extracted from ShopDeck should therefore preserve the relationships between these entities wherever the MCP exposes them.

Do **not** flatten the data unnecessarily if doing so would destroy important relationships.

---

# 5. Shiprocket Is a Separate Source

There is a small number of orders that are handled through Shiprocket.

These orders are:

> **completely independent of ShopDeck.**

They are not merely ShopDeck orders whose courier happens to be Shiprocket.

The operational boundary is:

```text
                    ┌───────────────┐
                    │   ShopDeck    │
                    │ ~99% orders   │
                    └───────┬───────┘
                            │
                            ▼
                    ShopDeck Projection
                            │
                            ▼
                       Brain Core


                    ┌───────────────┐
                    │  Shiprocket   │
                    │ small subset  │
                    └───────┬───────┘
                            │
                            ▼
                    Shiprocket Projection
                            │
                            ▼
                       Brain Core
```

Therefore:

**Do not attempt to use ShopDeck data to represent independent Shiprocket orders.**

Shiprocket will eventually have its own integration/source boundary.

For the current ShopDeck extraction task, focus on ShopDeck data only.

---

# 6. Current Goal

The immediate goal is to create an **initial ShopDeck operational dataset** for AaramBooks.

This is effectively a historical/backfill acquisition.

We want enough information to allow Brain Core development to proceed against realistic operational data instead of artificial examples.

The resulting data will eventually sit behind an AaramBooks-controlled boundary such as:

```text
ShopDeck MCP
      │
      │ read-only extraction
      ▼
AaramBooks ShopDeck Data Store
      │
      ▼
ShopDeck Adapter / Projection
      │
      ▼
Semantic Context
      │
      ▼
Brain Core
```

The MCP itself should **not** become a dependency embedded throughout Brain Core.

---

# 7. Why We Are Using the MCP

ShopDeck currently provides a read-only MCP interface through which its data is available.

The ShopDeck team has indicated that the MCP can be used to access the required data and that an approach can be to periodically export/synchronize the data into an external store.

That is exactly the direction we want to explore.

The current MCP should therefore be treated as:

> **a read-only data acquisition interface into ShopDeck.**

It is not the permanent architectural contract of Brain Core.

When ShopDeck's planned server-to-server API becomes available, the acquisition mechanism can eventually be replaced.

Conceptually:

```text
CURRENT

ShopDeck MCP
     ↓
Sync / Export
     ↓
AaramBooks Store


FUTURE

ShopDeck S2S API
     ↓
Sync / Export
     ↓
AaramBooks Store
```

The downstream AaramBooks architecture should remain the same.

---

# 8. Important Rule: Do Not Invent a Contract

The MCP-enabled ChatGPT must inspect the **actual ShopDeck schema and available data**.

Do not assume that a field exists because AaramBooks wants it.

Do not invent:

- table names
- column names
- relationships
- identifiers
- timestamps
- status values
- API structures
- shipment relationships
- return relationships

If a required piece of information does not exist in the available MCP data, explicitly report:

> **Not available / not exposed by the ShopDeck MCP.**

Do not manufacture a substitute.

---

# 9. First Task: Inspect the Complete ShopDeck Schema

Before extracting business data, inspect the available ShopDeck MCP schema.

Use the equivalent of:

```text
list_tables
```

if available.

The output should establish:

- all available tables
- table descriptions
- all columns
- data types where exposed
- column descriptions where exposed
- obvious primary identifiers
- relationships between tables
- date/timestamp fields
- status fields
- foreign-key-like fields
- fields that appear encrypted or transformed

Do **not** begin with arbitrary customer/order queries before understanding the schema.

---

# 10. Required Core Entities

The initial dataset should cover, wherever exposed:

### Customer

We need customer records and the authoritative customer identifier.

Potentially useful information includes:

- customer identifier
- customer number
- name
- contact information
- address information
- creation/update timestamps
- any other stable customer attributes exposed by ShopDeck

The actual fields must come from the MCP schema.

---

### Order

We need the complete order population available through ShopDeck.

Important information includes:

- authoritative order ID
- order status
- order timestamps
- customer relationship
- payment-related information if exposed
- fulfillment-related information if exposed
- cancellation information if exposed
- return/RTO relationship if exposed
- source/channel information if exposed

Again, use actual ShopDeck fields rather than assuming a canonical structure.

---

### Order Items

Order items are particularly important.

We need to establish:

```text
Order
  └── Order Item
        ├── SKU
        ├── quantity
        ├── item status
        └── shipment relationship
```

Important fields include, where available:

- order item identifier
- order ID
- SKU/item identifier
- item code
- quantity
- item-level status
- seller status
- customer status
- AWB/shipment relationship
- timestamps
- other item attributes

---

# 11. SKU / Product Identity

SKU identity is especially important because AaramBooks Inventory uses its own internal inventory model.

The ShopDeck dataset should therefore preserve the **ShopDeck SKU/item identifier exactly as ShopDeck exposes it**.

Do not convert it into an AaramInventory UUID unless the actual mapping is known.

The architecture should eventually allow:

```text
ShopDeck SKU
      │
      ▼
ShopDeck Adapter
      │
      ▼
AaramBooks semantic SKU identity
      │
      ▼
AaramInventory lookup
```

The external identifier should remain identifiable as originating from ShopDeck.

---

# 12. Shipment / AWB Data

Shipment information is critical.

Where exposed, extract:

- shipment identifier
- AWB number
- order relationship
- order-item relationship
- courier/service provider
- shipment status
- shipment creation time
- dispatch time
- delivery time
- cancellation/RTO information
- current status
- historical status information

Do not assume that one order equals one shipment.

The actual ShopDeck relationships should be preserved.

For example:

```text
Order
 ├── Item A
 │     └── Shipment X / AWB X
 │
 └── Item B
       └── Shipment Y / AWB Y
```

if that is how the actual data is structured.

---

# 13. Logistics Status

ShopDeck currently integrates with logistics/courier systems for the majority of orders.

Therefore, where available, extract logistics-related status information.

Important examples include:

- shipment status
- seller shipment status
- customer-facing status
- courier status
- dispatch
- in-transit
- out-for-delivery
- delivered
- failed delivery
- RTO
- returned
- cancelled

But:

> **Do not create a standardized status vocabulary during extraction unless ShopDeck itself exposes one.**

Preserve the original ShopDeck values.

Semantic normalization will be handled later by the AaramBooks adapter/context boundary.

---

# 14. Delivery Attempts / NDR

ShopDeck has indicated that delivery-attempt/NDR history is being added to the MCP.

Where this information is currently exposed, extract it.

Important fields include:

- shipment/AWB
- attempt number
- attempt timestamp
- NDR reason
- NDR code
- courier remarks
- attempt status
- subsequent resolution/status
- delivery outcome

The desired conceptual structure is:

```text
Shipment
   │
   ├── Delivery Attempt 1
   │      ├── timestamp
   │      ├── NDR code
   │      └── remarks
   │
   ├── Delivery Attempt 2
   │      ├── timestamp
   │      ├── NDR code
   │      └── remarks
   │
   └── Delivery Attempt N
```

If historical attempts are not yet exposed, report that explicitly.

---

# 15. Returns and RTO

Where available, extract return/RTO information.

We need to understand:

```text
Order
   │
   ├── Shipment
   │
   └── Return / RTO
```

Useful information includes:

- return identifier
- order relationship
- order-item relationship
- shipment relationship
- RTO status
- return status
- reason
- timestamps
- initiation date
- completion date
- relevant courier information

Do not infer a return relationship from status text if an actual relationship is available in another table.

---

# 16. Customer → Order Relationship

The extracted dataset must allow AaramBooks to determine:

```text
Customer
   ↓
Orders
```

We need to preserve the authoritative relationship exactly as exposed by ShopDeck.

This relationship is important for future Brain questions such as:

- customer order history
- repeat customers
- previous purchases
- customer-specific fulfillment history
- return history
- customer behavior

---

# 17. Order → Item Relationship

The dataset must preserve:

```text
Order
   ↓
Order Items
```

This is essential for:

- SKU intelligence
- product-level analysis
- inventory context
- order composition
- item-level fulfillment
- return analysis

---

# 18. Item → Shipment Relationship

Where exposed, preserve:

```text
Order Item
   ↓
Shipment / AWB
```

This is important because an order may contain multiple items and fulfillment may not map one-to-one.

Do not simplify the data into an assumption that every order has exactly one AWB.

---

# 19. Shipment → Delivery/NDR Relationship

Where available, preserve:

```text
Shipment
   ↓
Delivery Attempts
   ↓
NDR Events
   ↓
Final Outcome
```

This historical chain will eventually be important for AaramBooks intelligence.

For example, Brain may later need to reason about:

- repeated delivery attempts
- common NDR reasons
- courier performance
- customer-level delivery behavior
- SKU-level delivery patterns
- RTO patterns

Those analyses require historical events, not merely the current shipment status.

---

# 20. Historical Data Is Important

Do not extract only today's orders.

The objective is to establish a useful **initial historical operational dataset**.

Where the MCP permits it, determine the available historical range.

Report:

```text
Earliest available record
Latest available record
Approximate record count
```

for the major entities.

For example:

```text
Customers:       N
Orders:          N
Order Items:     N
Shipments:       N
Returns/RTO:     N
NDR Attempts:    N
```

Use actual counts obtained from ShopDeck.

Do not estimate.

---

# 21. Preserve Timestamps

For every entity/event where timestamps are available, preserve the original timestamp.

Important timestamps may include:

- created_at
- updated_at
- order time
- shipment creation
- dispatch
- delivery attempt
- NDR
- delivery
- cancellation
- return
- RTO

Do not discard timestamps merely because a current-status field exists.

Historical intelligence depends heavily on time.

---

# 22. Preserve Current State and Historical Events Separately

Where ShopDeck provides both:

```text
current status
```

and:

```text
historical events
```

preserve both.

For example:

```text
Shipment
 ├── current_status = delivered
 │
 └── status_history
       ├── shipped
       ├── in_transit
       ├── out_for_delivery
       └── delivered
```

Do not replace the historical sequence with only the final status.

---

# 23. Data Completeness

The MCP-enabled ChatGPT should identify any fields that are:

- NULL frequently
- encrypted
- unavailable
- derived
- ambiguous
- duplicated
- inconsistent

Do not silently clean these issues.

Instead provide a data-quality report.

For example:

```text
customer_number:
available but encrypted

AWB:
available for shipments, absent for cancelled orders

NDR history:
available from date X onward
```

This is much more useful than silently altering the data.

---

# 24. Data Extraction Should Be Incremental Where Possible

If the MCP allows filtering by:

- updated timestamp
- created timestamp
- order date
- shipment date
- ID ranges
- pagination

identify the safest mechanism for incremental synchronization.

The eventual model should support:

```text
Initial Backfill
       ↓
Incremental Sync
       ↓
Updated Projection
```

The initial extraction should therefore document which fields can be used as synchronization cursors.

For example:

```text
updated_at
```

if actually available and reliable.

Do not assume that `updated_at` is suitable merely because it exists. Report whether the data suggests it can serve as an incremental cursor.

---

# 25. Do Not Modify ShopDeck

The MCP connection is strictly read-only for this exercise.

Do not:

- create orders
- modify orders
- update customers
- modify shipments
- modify returns
- trigger operational actions
- write back to ShopDeck

This is a **data acquisition and analysis task only**.

---

# 26. Do Not Build Intelligence in This Extraction Step

The immediate objective is not:

> "Tell us what the business should do."

The immediate objective is:

> "Give AaramBooks the operational facts from which Brain Core can later reason."

Therefore prioritize:

```text
FACTS
RELATIONSHIPS
IDENTIFIERS
TIMESTAMPS
STATUS HISTORY
EVENT HISTORY
```

over interpretations.

---

# 27. Do Not Normalize Away Source Information

The raw ShopDeck meaning must remain recoverable.

For example, if ShopDeck says:

```text
seller_last_status = "XYZ"
```

do not replace it during extraction with:

```text
fulfillment_status = "in_transit"
```

unless explicitly asked to perform semantic mapping.

Instead preserve:

```text
source_system = ShopDeck
source_field = seller_last_status
source_value = XYZ
```

The later ShopDeck Adapter will perform semantic mapping into AaramBooks Context models.

---

# 28. Target Architecture

The long-term architecture is:

```text
                   SHOPDECK
                      │
                      │
                MCP / Future S2S
                      │
                      ▼
            ┌────────────────────┐
            │ ShopDeck Sync      │
            │ / Acquisition      │
            │ Boundary           │
            └─────────┬──────────┘
                      │
                      ▼
            ┌────────────────────┐
            │ ShopDeck           │
            │ Operational        │
            │ Projection         │
            └─────────┬──────────┘
                      │
                      ▼
            ┌────────────────────┐
            │ ShopDeck Adapter   │
            └─────────┬──────────┘
                      │
                      ▼
            ┌────────────────────┐
            │ Semantic Context   │
            │ Models             │
            └─────────┬──────────┘
                      │
                      ▼
            ┌────────────────────┐
            │ Brain Core         │
            └─────────┬──────────┘
                      │
                      ▼
            ┌────────────────────┐
            │ Intelligence       │
            └────────────────────┘
```

This separation is important.

---

# 29. Why We Want a Local Operational Projection

We do not want every Brain question to directly execute arbitrary analytical queries against the ShopDeck MCP.

Instead:

```text
ShopDeck
   ↓
synchronization
   ↓
AaramBooks-owned projection
   ↓
Brain
```

This provides:

- predictable access
- local queryability
- historical retention
- better performance
- reproducibility
- controlled semantic mapping
- independence from MCP availability
- easier future replacement of MCP with ShopDeck's S2S API

---

# 30. MCP Should Be an Acquisition Mechanism, Not Brain's Permanent Dependency

The current situation is transitional.

Today:

```text
ShopDeck MCP
```

may be the practical mechanism available to acquire the data.

Later ShopDeck expects to provide:

```text
Server-to-server API
Webhooks
Documented canonical contracts
```

When those become available:

```text
          TODAY

ShopDeck MCP
     ↓
Sync
     ↓
Projection


          FUTURE

ShopDeck S2S API
     ↓
Sync
     ↓
Projection
```

The projection and Brain architecture should not need to be redesigned.

Only the upstream acquisition layer should change.

---

# 31. Required Initial Dataset

At minimum, attempt to acquire the following logical dataset from the ShopDeck MCP:

```text
CUSTOMERS
    ↓
ORDERS
    ↓
ORDER ITEMS
    ↓
SHIPMENTS / AWBs
    ↓
DELIVERY / STATUS HISTORY
    ↓
NDR / DELIVERY ATTEMPTS
    ↓
RETURNS / RTO
```

Plus:

```text
SKU / ITEM IDENTIFIERS
```

and all available relationships between them.

---

# 32. Preferred Extraction Order

Use this order:

### Step 1 — Schema

Inspect all available tables.

### Step 2 — Relationships

Determine how the tables connect.

### Step 3 — Identifiers

Identify authoritative IDs.

### Step 4 — Historical range

Determine how far back data is available.

### Step 5 — Counts

Determine approximate record counts.

### Step 6 — Core entities

Extract customers, orders, order items.

### Step 7 — Fulfillment

Extract shipments/AWBs and logistics information.

### Step 8 — Events

Extract status histories, delivery attempts and NDR.

### Step 9 — Returns

Extract returns/RTO.

### Step 10 — Data quality

Identify missing, encrypted, ambiguous or inconsistent fields.

### Step 11 — Export

Produce a structured dataset suitable for importing into an AaramBooks-controlled data store.

---

# 33. Expected Output From the MCP Chat

The MCP-enabled ChatGPT should not merely answer with a textual summary.

We need actual data.

The preferred output should include:

### A. Schema report

```text
Table
Column
Type
Description
Relationship
```

### B. Dataset inventory

```text
Entity
Record count
Date range
Primary identifier
Important relationships
```

### C. Extracted data

Prefer machine-readable files such as:

```text
CSV
JSON
JSONL
Parquet
```

depending on what the MCP environment allows.

If the MCP chat cannot directly create/download files, it should provide the data in a form that can be exported without losing records.

---

# 34. Suggested File Structure

If files can be produced, prefer a structure similar to:

```text
shopdeck-initial-export/
│
├── README.md
│
├── schema/
│   └── shopdeck-schema.json
│
├── customers/
│   └── customers.jsonl
│
├── orders/
│   └── orders.jsonl
│
├── order-items/
│   └── order-items.jsonl
│
├── shipments/
│   └── shipments.jsonl
│
├── shipment-events/
│   └── shipment-events.jsonl
│
├── delivery-attempts/
│   └── delivery-attempts.jsonl
│
├── returns/
│   └── returns.jsonl
│
└── data-quality/
    └── data-quality-report.md
```

This is a target structure, not a claim that these exact entities/tables exist in ShopDeck.

If ShopDeck exposes different structures, preserve the actual structure and document the mapping.

---

# 35. Preserve Source Metadata

Every exported dataset should ideally identify:

```text
source_system = ShopDeck
source_table = <actual table>
extracted_at = <timestamp>
```

Where useful, also preserve:

```text
source_record_id
```

This will make later reconciliation much easier.

---

# 36. No Silent Deduplication

Do not silently remove duplicate records.

If duplicate-looking records exist:

```text
identify them
report them
preserve them
```

unless the authoritative ShopDeck key clearly establishes that one is a duplicate representation.

A later ingestion process can apply controlled deduplication.

---

# 37. No Silent Data Transformation

Do not silently:

- rename values
- convert statuses
- merge records
- discard NULLs
- convert IDs
- infer missing relationships
- fabricate timestamps
- infer courier names

Preserve source truth first.

Transformation belongs in the AaramBooks integration boundary.

---

# 38. Important Relationship to AaramInventory

AaramBooks also has an inventory truth system.

ShopDeck order items may identify products/SKUs differently from AaramInventory.

Therefore:

```text
ShopDeck SKU
       │
       ▼
ShopDeck identity
       │
       ▼
AaramBooks SKU mapping
       │
       ▼
AaramInventory
```

The ShopDeck extraction should **not** attempt to solve this mapping unless the MCP itself exposes an authoritative mapping.

The purpose of the initial ShopDeck dataset is to preserve the ShopDeck identity accurately.

---

# 39. Brain Core's Future Semantic Layer

Eventually Brain Core should see semantic contexts rather than raw ShopDeck tables.

For example:

```text
ShopDeck raw data
       ↓
ShopDeck Adapter
       ↓
OrderContext
CustomerContext
FulfillmentContext
ShipmentContext
InventoryContext
       ↓
Brain Core
```

This allows Brain Core intelligence to remain independent of ShopDeck's physical schema.

If ShopDeck changes:

```text
ShopDeck schema
       ↓
ShopDeck Adapter
       ↓
same semantic Context
       ↓
Brain
```

rather than:

```text
ShopDeck schema
       ↓
Brain code everywhere
```

---

# 40. Future Questions Brain Should Eventually Be Able to Answer

The initial dataset should make it possible to build toward questions such as:

### Customer

- What has this customer ordered?
- How many orders has the customer placed?
- What products has the customer purchased?
- How many returns/RTOs are associated with the customer?

### Order

- What is the current state of this order?
- What items are in the order?
- Which shipment/AWB is associated with each item?
- What happened to the order historically?

### Shipment

- Where is the shipment in its lifecycle?
- How many delivery attempts occurred?
- What NDR reasons were recorded?
- Was it eventually delivered or returned?

### Product

- Which SKUs are being ordered?
- Which SKUs have high return/RTO rates?
- Which SKUs are associated with delivery issues?

### Business intelligence

Eventually, Brain should be able to reason across:

```text
Customer
+
Order
+
SKU
+
Shipment
+
Courier
+
NDR
+
Return/RTO
+
Inventory
```

This is why preserving the relationships is more important than simply obtaining a flat order export.

---

# 41. Important: Do Not Limit Extraction to What Brain Needs Today

The first dataset should be sufficiently broad to support future intelligence development.

However, this does **not** mean extracting every possible field indiscriminately.

The principle is:

> Preserve operational information that is relevant to the customer → order → item → shipment → delivery/NDR → return lifecycle.

Do not extract unrelated or unnecessary data simply because it is available.

---

# 42. Security and Privacy

The extracted dataset may contain sensitive customer information.

Handle it as operational business data.

Do not:

- expose credentials
- expose OAuth tokens
- expose MCP authentication secrets
- include secrets in exported files
- invent or derive authentication credentials

Customer information should only be extracted where it is genuinely required for the AaramBooks operational context.

---

# 43. The Immediate Mission

The MCP-enabled ChatGPT should understand the mission as:

> **"Help us establish the initial ShopDeck operational dataset for AaramBooks Brain Core."**

Not:

> "Build a ShopDeck integration."

Not:

> "Design an imaginary ShopDeck API."

Not:

> "Build Brain Core intelligence."

Not:

> "Replace ShopDeck."

The immediate mission is:

```text
Inspect
   ↓
Understand
   ↓
Extract
   ↓
Preserve
   ↓
Package
   ↓
Deliver
```

---

# 44. Final Instructions to the MCP-Enabled ChatGPT

You are connected directly to the **ShopDeck MCP**.

AaramBooks is building **Brain Core**, an intelligence layer that must reason over real operational business data.

ShopDeck is the primary operational source for approximately 99% of the business's orders and currently contains the corresponding logistics/courier information for those orders.

We need you to help create the **initial ShopDeck operational dataset** that will be imported into an AaramBooks-controlled data store.

### Do the following:

1. Inspect the complete ShopDeck MCP schema first.
2. Identify all relevant customer, order, order-item, SKU/item, shipment/AWB, logistics-status, delivery-attempt/NDR, return/RTO entities.
3. Identify the authoritative identifiers.
4. Identify the actual relationships between those entities.
5. Determine the available historical date range.
6. Determine record counts where feasible.
7. Extract the relevant historical operational data.
8. Preserve original ShopDeck identifiers and source values.
9. Preserve timestamps.
10. Preserve status/event history wherever available.
11. Preserve delivery-attempt/NDR history wherever available.
12. Preserve return/RTO relationships wherever available.
13. Identify missing, encrypted, ambiguous or incomplete fields.
14. Do not invent fields or relationships.
15. Do not normalize source values unless explicitly requested.
16. Do not modify any ShopDeck data.
17. Do not attempt to represent independent Shiprocket orders.
18. Produce a structured export suitable for loading into an AaramBooks-controlled operational projection.
19. Produce a schema/data dictionary and data-quality report alongside the data.
20. Clearly distinguish **actual data obtained from ShopDeck** from assumptions or recommendations.

### Most important:

**We need the actual data, not merely a description of how to obtain the data.**

If the MCP environment can generate downloadable files, create the export files.

If it cannot generate files directly, provide the largest practical machine-readable export and clearly explain the safest way to obtain the complete dataset without losing records.

Do not fabricate a ShopDeck REST API contract.

Do not assume fields that are not present.

Do not tell us to wait for the future ShopDeck S2S API.

**Use the ShopDeck MCP that is available right now and help us establish the initial operational data foundation for AaramBooks Brain Core.**