# Architectural Documentation Rule

Whenever a new architectural finding or major implementation detail is discovered, or whenever an existing architectural principle or boundary is modified, you MUST:
1. Identify the relevant architectural document in the `docs/` directory.
2. Modify the relevant document without fail to reflect the new reality.
3. If no suitable document exists, create a new one in the appropriate architectural domain folder.
4. ALWAYS prefer inserting Mermaid diagrams and structured Markdown tables in documentation `.md` files to maximize visual clarity, architectural rigor, and immediate scannability.

Do not allow the implementation code to drift from the architectural documentation.
