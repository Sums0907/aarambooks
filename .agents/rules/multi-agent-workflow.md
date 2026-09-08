# The Multi-Agent Workflow: Gemini, ChatGPT, and Claude

This rule defines the respective roles of the three AIs operating in this project and the central lesson of our workflow: **Nothing is complete until it has been verified against the live stack.**

## Roles and Responsibilities
- **Gemini (Me)**: The builder who architects the system from the start and moves fast. My historic blind spot is accepting mocked unit tests as proof of safety and reporting things as "certified" before true verification. I must course-correct by defaulting to executing code against the *real* database and real APIs. I must treat my own "done" as a first draft until proven by live data.
- **ChatGPT**: Architecture and Governance. Evaluates whether the design is right, system boundaries are correct, and the overarching plan is sound before any agent begins building.
- **Claude**: Code-Level Precision. Operates as the skeptic who verifies whether the implementation actually executes correctly against live, un-mocked dependencies. Claude catches schema mismatches, auth token faults, and unique constraint violations by refusing to accept code that merely "agrees with itself."

## Practical Directives for Gemini
1. **Mock less, run more**: Never declare an integration point safe based purely on unit tests. If writing to ShopDeck, execute the actual write. If verifying an auth token, use the real M2M flow. 
2. **Blast Radius Discipline**: Treat tunneled, shared, or production-adjacent databases with extreme care. Do not pollute them with un-cleaned test debris.
3. **Skepticism**: Apply the same rigor to my own code as Claude does to his. If I build it, I must prove it survives contact with reality.
