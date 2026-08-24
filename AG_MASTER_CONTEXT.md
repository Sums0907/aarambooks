# AG Master Context — AaramBooks

## Project Identity

AaramBooks is the overarching ecosystem for building an AI-native business operating system.

Core principle:

> Business systems create truth. Aaram Brain creates intelligence from that truth.

AaramBooks is composed of independent business domains and an intelligence layer.

## Existing Business Systems

### AaramIdentity
Owns identity, authentication, authorization, roles and permissions.

### AaramInventory
Owns inventory truth including products, SKUs, inventory state, stock movements and inventory ledger.

### AaramPacking
Owns physical warehouse execution truth including packing workflows and operational packing events.

## Aaram Brain

Aaram Brain is the intelligence and decision layer of AaramBooks.

It does not replace business systems.
It does not own operational truth.
It does not become a duplicate ERP/database.

Structure:

Aaram Brain
- Brain Core
- Intelligence Domains

Brain Core provides shared intelligence capabilities.

Initial Intelligence Domains:
- NDR Intelligence
- Customer Query Intelligence

## Current Phase

Architecture documentation phase completed.

Implementation must follow:
Architecture → Data Models → Contracts → Development → Validation

AG must use repository documentation as the source of truth.
