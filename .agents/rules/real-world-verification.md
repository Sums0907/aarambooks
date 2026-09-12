---
description: Critical rule for marking work as 'done'. Code completeness is never sufficient; real-world execution against live dependencies is required.
---

# Real-World Verification Protocol

Treat "the code is written/looks right" and "I ran it against the real thing and watched it work" as **two completely different milestones**.

Never mistake the first milestone for the second.

## The Core Lesson
Historically in this codebase, the most critical bugs (silent payload drops, AZM database initialization failures, abandoned deployment patterns) were invisible during code inspection and synthetic tests. They were ONLY caught when the code was actually executed against the real external dependency (e.g., hitting the live ShopDeck API, running migrations against a real PostgreSQL instance, deploying to the actual VPS).

## Agent Directives
When implementing features or fixing bugs in this repository, you MUST abide by the following:

1. **Absence of Evidence is not Proof of Absence**: Do not assume the shape of an API response or database state just by reading the consuming code. You must fetch and read the raw, live output from the actual system before building integrations around it.
2. **Execute Against Reality**: A task is never "done" just because the unit tests pass or the code looks logically sound. You must run the actual code (via scripts, curls, or live endpoints) against the real external dependencies (ShopDeck, Identity, PostgreSQL, Sarvam) and verify the resulting side-effects.
3. **No Synthetic Shortcuts**: Do not rely entirely on synthetic fixtures or mocked databases for final verification if a real connection is available.

If you cannot verify against the live system yourself, you must explicitly hand over the exact commands or scripts for the USER to run in their environment, and you must refuse to mark the task as complete until the user confirms the real-world execution succeeded.
