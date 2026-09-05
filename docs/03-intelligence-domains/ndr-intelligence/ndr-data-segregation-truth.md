# NDR-ID Fundamental Truth: Data Retention & Segregation

**Document Identifier:** `NDR-ID-DATA-SEGREGATION-V1`  
**Status:** Fundamental Architectural Truth  
**Classification:** Core Engineering Principle  

## 1. The Core Principle: Data is Digital Gold

In the Non-Delivery Report Resolution Intelligence Domain (NDR-ID), we recognize that data generated during customer interactions, carrier events, and AI decision-making processes is invaluable. We operate under the strict principle that **we do not waste data**.

However, we must maintain rigid architectural boundaries between cognitive intelligence (Aaram Brain) and operational execution (Business Systems like ShopDeck). Therefore, we employ a strict **Dual-Persistence Segregation Strategy**.

## 2. The Dual-Persistence Segregation Strategy

We store **both** the raw, unfiltered real-world data AND the finalized, actionable intelligence, but we store them across fundamentally different architectural boundaries based on system ownership and purpose.

### A. The Raw "Digital Gold" (Owned by Aaram Brain)
The exact, raw, unfiltered real-world data is captured and persisted permanently inside **Aaram Brain's internal database** (specifically, the MongoDB `customer_engagement_events` collection).

* **What is stored here:** 
  * Raw courier webhook JSON payloads.
  * Unedited customer IVR transcripts and SMS replies.
  * Granular event timestamps and provider metadata.
* **Why it belongs here:** 
  Aaram Brain acts as the ultimate data lake for human and machine interactions. It requires this raw, noisy data to continuously train its LLMs, run historical backtests, discover new recovery patterns, and improve its semantic mappers. 
* **The Rule:** We never throw away raw signals. Brain hoards the raw digital gold for continuous learning.

### B. The Filtered Operational Intelligence (Owned by Business Systems)
The highly structured, filtered, and canonical intelligence is pushed across the integration boundary and persisted in the **Business System's Database** (e.g., ShopDeck's Postgres Database via `shopdeck_ndr_intelligence_log`).

* **What is stored here:**
  * Target AWB / Order Identifiers.
  * Final AI Recommendations (e.g., `seller_reattempt`, `courier_dispute`).
  * Diagnosed Root Cause and standardized reasoning.
* **Why it belongs here:** 
  Business systems only care about structured operational truths they can act on or report on. They do not need the noisy raw webhooks or the AI's internal thought process. They require finalized actionable data to render Action Reports and execute physical logistics.
* **The Rule:** ShopDeck only stores the refined, operational diamond needed for execution.

## 3. Summary of Architectural Impact

If we dumped the raw webhook data into ShopDeck, we would pollute the Business System with unstructured noise, breaking the clean separation of concerns. 

If we threw the raw data away after generating a recommendation, we would starve Aaram Brain of its future training fuel, destroying our ability to build a continuous learning loop.

By rigidly segregating this persistence, **Aaram Brain retains the raw context required to evolve its intelligence, while ShopDeck retains the exact structured parameters required to drive business value.**
