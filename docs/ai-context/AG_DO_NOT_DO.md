# AG Do Not Do

AG must not:

- Create duplicate customer, inventory, product or operational truth.
- Move business ownership into Aaram Brain.
- Bypass APIs or event contracts.
- Access another domain database directly.
- Modify stable modules without architectural review.
- Create schemas without approved data models.
- Add technology choices that violate provider independence.
- Mix Intelligence Domain logic into Brain Core.
- Implement features without reading the relevant architecture documentation.

Avoid:
- Quick fixes that create coupling.
- Hidden dependencies.
- Uncontrolled scope expansion.

---

# Cross-Module Modification Prohibition

AG must not:

- Modify another module's architecture without approval.
- Resolve cross-domain conflicts inside a single module.
- Introduce new responsibilities into existing components.
- Change ADR decisions silently.
- Expand Brain Core because one Intelligence Domain requires a capability.

When a module requirement impacts another module:

- Stop.
- Identify the architectural impact.
- Report the conflict.
- Request architecture-level resolution.
