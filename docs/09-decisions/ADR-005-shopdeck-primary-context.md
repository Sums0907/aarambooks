# ADR-005: ShopDeck as Primary Operational Context Provider

**Status:** DRAFT
**Date:** 2026-08-26

## Context
Phase 4 of the Brain Core implementation was originally designated to build internal operational integration adapters for AaramInventory and AaramPacking.
An independent architectural reconciliation audit revealed that ShopDeck natively tracks the end-to-end customer journey, order state, payment state, shipment/NDR state (`seller_last_status`, `awb_no`, `delivery_time`, `rto_initiated`), and return states.

## Decision
1. **ShopDeck is the Primary Context Provider:** ShopDeck is the primary source from which Brain Core obtains operational context (customer, order, SKU, shipment, delivery, RTO, timestamps).
2. **Brain does not own operational truth:** Brain Core's semantic context, intelligence, and decisions are distinct from operational system truth. Brain models represent Brain's semantic requirements, not a mirror of ShopDeck payloads.
3. **AaramInventory provides quantity_on_hand enrichment only:** Brain Core uses AaramInventory solely when authoritative inventory quantity is required (ShopDeck -> SKU ID -> AaramInventory -> quantity_on_hand). `confidence_score` is explicitly outside Brain's context boundary.
4. **AaramPacking is NOT a Context Provider:** AaramPacking is a physical warehouse execution application. Brain must not query it to reconstruct operational truth. AaramPacking remains a potential future Action Engine execution target, separated from Context.
5. **Acknowledge ShopDeck headless connectivity limitation:** The only ShopDeck connectivity currently available is the interactive OTP-based MCP, which prevents immediate headless implementation for Brain. This limitation is an external dependency and does NOT invalidate this approved architecture. 

## Consequences
- **Positive:** Brain Core retrieves a unified, authoritative context of an order from a single system (ShopDeck). Eliminates data duplication.
- **Positive:** AaramPacking remains fully decoupled from intelligence processing, preserving its bounded context.
- **Positive:** AaramInventory's context boundary is clearly constrained to `quantity_on_hand`.
- **Negative:** Requires immediate un-freezing and refactoring of Phase 4 implementation backlog to reflect ShopDeck's external dependency.
- **Blocker:** Machine-to-Machine (M2M) authentication in AaramIdentity must be solved to access AaramInventory. Headless API credentials for ShopDeck must be procured from the external dependency to unblock ShopDeck context assembly.
