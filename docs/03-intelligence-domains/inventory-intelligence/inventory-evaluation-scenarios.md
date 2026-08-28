# Inventory Intelligence Evaluation Scenarios

## Purpose

This document catalogs the 17 core evaluation scenarios used to validate the `inventory-intelligence` domain. These questions are *representative evaluation scenarios* used to prove that the generic domain works and to discover the required breadth of the Inventory Context vocabulary.

The architecture remains generic. Passing these questions does not define the domain's permanent capability boundary.

---

## Scenario Categories & Context Capability Gaps

For each category, we identify the business facts required, the context capability category, and whether it currently exists or represents a Context Capability Gap in the Brain Core Context Layer.

### 1. Exception Analysis & Diagnostics
- **Q1:** "Why is there an open exception of -50 units on SKU 'Physics Textbook'?"
- **Q11:** "Are there any SKUs where the physical warehouse stock is consistently generating negative exceptions month over month?"
- **Required Facts:** Exceptions over time, recent inventory movements.
- **Context Category:** Inventory Exceptions, Inventory Movements.
- **Capability Status:** **GAP**. Context Layer currently cannot resolve historical exceptions or movements.

### 2. Third-Party Jobwork & Material Leakage
- **Q2:** "Which job worker has the highest volume of raw materials pending return for over 30 days?"
- **Q6:** "What is the actual yield percentage for Vendor X?"
- **Q8:** "Which SKUs have seen the highest rate of scrap or wastage during Jobwork this month?"
- **Q9:** "What is the total financial value of all raw materials currently sitting idle at third-party job worker locations?"
- **Required Facts:** Jobwork issues, receipts, scrap quantity, pending quantity, vendor mapping.
- **Context Category:** Jobwork Context, Valuation Context.
- **Capability Status:** **GAP**. Context Layer currently cannot resolve Jobwork material reconciliation.

### 3. Availability & Production Readiness
- **Q3:** "Is SKU-1234 available for fulfillment? If out of stock, is there pending stock expected from a jobworker soon?"
- **Q7:** "Which finished goods are out of stock, but we have enough raw materials in the warehouse to start a production run immediately?"
- **Q14:** "Do we have substitute raw materials defined in the BOM to assemble this order?"
- **Required Facts:** Current balance, BOM product structure, pending jobwork stock.
- **Context Category:** Inventory Availability, SKU/Catalog Context, Jobwork Context.
- **Capability Status:** **PARTIALLY AVAILABLE** (Availability exists), **GAP** (BOM and Jobwork missing).

### 4. Aggregation, Ranking, and Factual Lookup
- **Q4:** "Which top 10 SKUs drove the highest sales volume this month based strictly on dispatch movements?"
- **Q5:** "What is the exact box dimension and weight for Shipping SKU-999 to calculate freight?"
- **Q12:** "Identify any raw materials that are in stock but haven't been consumed in any BOM or jobwork in the last 6 months."
- **Q17:** "List all Active SKUs that are missing a linked Unit of Measure or a Pricing model."
- **Required Facts:** Aggregated dispatch movements, master data dimensions, non-consumption history, pricing/UoM links.
- **Context Category:** Inventory Movements, SKU/Catalog Context.
- **Capability Status:** **PARTIALLY AVAILABLE** (Basic SKU/UoM exists via existing endpoints conceptually), **GAP** (Movements aggregation).

### 5. Financial Reconciliation & Ledger Anomaly Detection
- **Q10:** "Calculate the total Cost of Goods Sold (COGS) for SKU-ABC based on actual unit costs in the movement ledger last quarter."
- **Q13:** "Show me a reconciliation of the 'Inventory Asset' ledger account against the physical warehouse balances."
- **Q15:** "Are there any 'POSTED' sales movements in the ledger that do not have a corresponding invoice reference ID?"
- **Q16:** "Are there any Jobwork receipts where physical stock arrived but the financial journal wasn't updated?"
- **Required Facts:** Unit costs, ledger accounts, physical balances, invoice references, journal entries.
- **Context Category:** Inventory Ledger & Valuation, Inventory Movements.
- **Capability Status:** **GAP**. Context Layer currently cannot resolve financial ledgers and COGS context.
