# AaramBooks Brain Architecture — Data Models Overview

## Purpose

This document defines the conceptual data model foundation for AaramBooks Brain Architecture.

The Data Models layer establishes how information, knowledge, intelligence context, reasoning outputs, decisions, actions, and memory are conceptually represented.

## Architectural Principle

> Business systems create truth. Aaram Brain creates intelligence from that truth.

Business systems remain the complete owners of operational truth and physical data schemas. Aaram Brain transforms trusted business information into contextual understanding, reasoning, decisions, and intelligent actions without owning the underlying data structures.

## Semantic Context vs Physical Domain Models

With the introduction of the **Stage F Generic Context Capability Framework**, Brain Core enforces a strict separation between Semantic Models and Physical Models:

### 1. Semantic Models (Brain Core Owned)
Brain Core operates exclusively using Semantic Models. These represent the *intent* of what is required and the *opaque evidence* of what is returned.
- **`ResolvedSemanticRequirement`:** The formal request for business truth (e.g., "SKU X, Warehouse Y").
- **`EvidenceItem`:** The generic, opaque JSON payload returned by a business system. Brain Core does not parse or validate the internal schema of this payload.

### 2. Physical Domain Models (Business System Owned)
External business systems define and own the physical reality.
- **e.g., `InventoryContext`, `ShipmentContext`**
These physical schemas dictate how the business system structures its authoritative facts. They are entirely internal to the respective business systems (or their Context Exposure Modules) and must NEVER be imported, defined, or hardcoded into Brain Core's generic routing logic.

*(Note: Certain legacy models like `CustomerContext` and `ShipmentContext` currently exist in `src/brain_core/models/contexts.py` as temporary transitional dependencies for Event Bus routing. They are explicitly marked as legacy and are excluded from the generic Context Capability framework.)*

## Objectives

- Define information categories used by Aaram Brain (Semantic intent, Actions, Decisions).
- Establish absolute ownership boundaries (Physical Schemas = Business Systems).
- Define relationships between truth and intelligence.
- Provide conceptual foundations for intelligence domains.
