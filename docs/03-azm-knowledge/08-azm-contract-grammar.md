# AZM Canonical Markdown Contract Grammar

**Document Reference:** `docs/03-azm-knowledge/08-azm-contract-grammar.md`
**System Name:** AZM
**Status:** Canonical Reference

---

## 1. Document Metadata (YAML Frontmatter)
Every contract must start with a YAML frontmatter block defining its global identity.

```yaml
---
source_bs: "{business_system_id}"
namespace_name: "{namespace_id}"
namespace_classification: "AARAM_NATIVE | EXTERNAL_CHANNEL"
namespace_description: "{Description of the namespace}"
contract_version: "{version string}"
---
```

## 2. Semantic Concepts
Defined in the Semantic Contract. Each concept uses an H3 block followed by a strict key-value list.

```markdown
### Concept: {Concept Name}
- **Semantic Key:** {namespace}.{type}.{name}
- **Concept Type:** ENTITY | ATTRIBUTE | TEMPORAL | AGGREGATION | RELATIONSHIP | STATE
- **Definition:** {String definition}
- **Aliases:** {comma-separated aliases, or empty}
```

## 3. Relationships
Defined in the Semantic Contract using a standard Markdown table.

```markdown
### Relationships

| Source Key | Target Key | Type | Derivation Rule | Source Element |
|---|---|---|---|---|
| {source_semantic_key} | {target_semantic_key} | {CONTAINS|HAS|MAPS_TO|RELATED_TO|PART_OF} | {rule name} | {description of rule} |
```

## 4. External Mappings
Defined in the Semantic Contract for `EXTERNAL_CHANNEL` classifications.

```markdown
### External Mappings

| Native Concept | External System | External Key | Display Name |
|---|---|---|---|
| {aaram.native.key} | {shopdeck} | {customer_sku_short_id} | {Display Name} |
```

## 5. Schematic Views
Defined in the Schematic Contract. Each view uses an H3 block followed by a description list item, and a Markdown table for columns.

```markdown
### View: {view_name}
- **Description:** {View description}

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| {column_name} | {TEXT/INTEGER/etc} | {true/false} | {true/false} | {semantic_key or None} | {description or constraints} |
```

## 6. Parsing Rules
- The parser expects exact matches on the bolded keys (e.g. `- **Semantic Key:**`).
- Tables must have the exact column headers defined above.
- Unstructured Markdown (narrative text, alerts, explanations) can exist anywhere *outside* of these strict blocks. The parser will ignore narrative text, ensuring the contracts remain human-readable documents.
