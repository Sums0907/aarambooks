---
description: Strict verification protocol to prevent false-positive success claims on code changes.
---

# Post-Change Verification Protocol

After every non-trivial code addition or refactor, and before reporting it as done or verified, you MUST strictly follow this protocol:

1. **Identify the Live Wiring**: Identify what is *actually* wired live in `main.py` (or the relevant composition root) — not what merely exists in the file. If you added or replaced a class, confirm which exact class is constructed in the live path.
2. **Execute the Real Class**: Write a test that instantiates that *exact live class* with realistic, production-shaped payloads, and actually runs it end-to-end. Do NOT use mocks that stub out the method under test, and do NOT test a legacy or sibling class with the same shape.
3. **Show Raw Evidence**: Paste the literal `pytest` (or equivalent) output instead of summarizing it. Never just say "should work" or describe what it checks.
4. **Run the Full Suite**: Run the full regression suite, not a hand-picked subset. If a subset is skipped for speed, state explicitly which subsets were skipped and why.
5. **Exact Metrics**: Report exact numbers (e.g., "461 passed, 8 failed"). Never repeat a bare "PASS" with no numbers.
6. **No Silent Retries**: Immediately report any failure before proposing next steps. Never silently narrow the test scope or retry until it's green.
7. **Refrain from Premature Confidence**: Never claim "fully cut over", "done", or "verified" without raw output proving the live execution path was tested. If verification was partial, say exactly what was and wasn't checked.
8. **Full-Stack Verification**: Never declare a full-stack feature "rock solid" or "passed" based solely on backend API tests. If a change involves frontend code (e.g. React/JSX), you must explicitly verify that the frontend compiles successfully and renders without syntax or runtime reference errors before handing it off.
