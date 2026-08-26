# Architectural Documentation Governance

Purpose:
Prevent architecture drift between implementation and documented design.

Rules:

- New architectural discoveries must be reflected in the appropriate docs/ document.
- Changes to ownership boundaries must update architecture documentation.
- New implementation patterns that affect architecture must be documented.
- If no suitable document exists, create one in the correct architectural domain folder.
- Implementation should not proceed with undocumented architectural changes.

Relationship:

.agents/rules/architectural-documentation.md
controls automation behavior.

docs/
contains the human-readable architectural record.
