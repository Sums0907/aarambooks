# Open Decisions Register Synchronization Rule

**Purpose:**
Automatically maintain the central `docs/09-decisions/open-decisions-register.md` without requiring explicit user prompts.

**Instructions:**
1. Whenever you discover or define a new "Open Decision" or "Open Question" while writing or updating architectural and technical design documents, you MUST automatically append it to the appropriate section of `docs/09-decisions/open-decisions-register.md`.
2. Whenever an existing "Open Decision" is resolved, clarified, or decided upon in the conversation or in another document, you MUST automatically update `docs/09-decisions/open-decisions-register.md` to move it from the "OPEN" section to the "CLOSED" section, documenting the final decision, reasoning, and architectural impact.
3. You do not need to ask for permission to update the register; treat it as a mandatory, automatic task whenever decisions change state.
