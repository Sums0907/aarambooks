# Azm Knowledge Architecture

Welcome to the Azm Knowledge documentation. This directory is the dedicated space for Azm architecture, namespace definitions, and intelligence subsystems that make up the "Azm" layer in the 4-Box Architecture.

## Overview

Azm acts as the central knowledge registry (Container 3) providing canonical entity definitions and schemas to the rest of the application. It ensures that Intelligence Domains (like Inventory) have access to structured views without needing to hardcode schemas or maintain tight couplings with backend tables.

## Namespaces

The system is partitioned into the following domains:

- **Inventory** (`src/azm/namespaces/inventory.py`)
  - Entities: `sku`, `warehouse`, `jobworker_vendor`, `supplier`, `bom_component`
  - Public Views: 
    - `vw_stock_balances`
    - `vw_bom_components`
    - `vw_jobwork_status`
    - `vw_suppliers`

- **NDR (Logistics)** (`src/azm/namespaces/ndr.py`)
  - Initial schema definitions and terms for NDR / Logistics intelligence.

## Qwen Fine-Tuning Flywheel

The schemas and data from Azm namespaces are used to continuously feed our Text-to-SQL Engine. By strictly typing our public views in Azm, we provide a robust and predictable basis for fine-tuning our localized LLMs (like Qwen) for better domain-specific reasoning and accurate SQL generation.
