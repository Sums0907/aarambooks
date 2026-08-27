# ShopDeck Sample Data

## Purpose
This directory contains sample JSON payloads corresponding to ShopDeck API responses. These samples are used as test fixtures for the Business Adapters (e.g., `ShopDeckCustomerAdapter`) to validate mapping and error boundaries without requiring live network calls to the actual ShopDeck API.

## Raw vs. Scenario Fixtures
- **`raw/`**: Contains exact (but sanitized) unmodified JSON dumps directly from the ShopDeck API to serve as the baseline reference material.
- **Scenario directories (e.g., `customer/happy-path/`, `order/cancelled/`)**: Contain test fixtures derived from the raw data. These are specifically structured or intentionally malformed to test particular business edge cases, missing fields, or domain error translations.

## Naming Conventions
- Files should be named descriptively ending in `.json` (e.g., `customer-summary-happy-path.json` or `order-missing-tracking.json`).

## Synthetic and Sanitized Data Only
**CRITICAL**: In accordance with the [Raw Data Protection Standard](../../docs/10-implementation-plan/engineering-foundation-standard.md), all data in this directory must be synthetic or heavily sanitized.
- **RAW EXTERNAL / OPERATIONAL DATA MUST NEVER BE COMMITTED TO GITHUB.**
- Do not commit real customer PII (names, phone numbers, addresses, emails).
- Do not commit real order data that exposes sensitive customer information.
- Do not commit real API tokens, secrets, or financial transaction identifiers.

**Note on Current Fixtures:**
The test fixtures provided here (such as `customer/happy-path/customer-summary.json`) are completely synthetic and sanitized. They are derived directly from the column structure of the raw local ShopDeck CSV export but contain absolutely zero original real names, phone numbers, or financial values, rendering them safe for repository testing and automated CI workflows.

## Scope
This structure is currently **ShopDeck-only**. Do not create folders for Amazon, Flipkart, AaramIdentity, AaramInventory, or AaramPacking here until those specific adapters are actively being implemented and require test fixtures.
