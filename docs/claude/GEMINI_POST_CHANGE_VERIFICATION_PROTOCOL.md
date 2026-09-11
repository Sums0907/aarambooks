# Post-change verification protocol (for Gemini)

Written by: Claude
Date: 2026-09-11
Status: a matching rule file was drafted at `.agents/rules/post-change-verification.md` and
then removed - it was created without authorization (the user asked for the draft to be
vetted, not written), so it does not exist right now. This document remains the only copy of
the protocol until the user or Gemini's own approval flow actually creates the rules-file
version.
Why this exists: the ShopDeck catalog cutover was reported as "fully cut over... 7 relevant
CCC wiring tests passed... only failure was unrelated." The class actually wired live in
main.py (ShopDeckMasterCCCBuilder) had a guaranteed NameError crash on every real order with
items, and a second pydantic ValidationError crash right behind it - because the cited test
file only ever instantiated the *old*, unused legacy class. Both were found only by directly
instantiating the live class with realistic data and running it, not by trusting a green test
run. This is the standing rule that incident should have followed.

## The rule, in one sentence

**A change is not done until it has been run - not imported, not unit-tested in isolation,
actually executed end-to-end with the class/function that is really wired into the live
path - and the exact command and its exact output are shown, not summarized as "passed."**

## Required after every non-trivial addition or refactor

1. **Identify what's actually wired live**, not what merely exists. If a change adds or
   replaces a class (adapter, builder, handler), find every place it's constructed in
   `main.py` or equivalent composition root, and test *that* object graph - not a same-named
   sibling, not the class it replaced, not an isolated unit in a vacuum.
2. **Write a test that instantiates the real, live class with realistic data and actually
   calls it** - not a mock that stubs out the method under test, not an assertion against a
   hand-built object that skips the code path entirely. If the new code parses a payload
   shape (a JSON field, an API response key), the test's fixture must be shaped like the real
   thing, not an idealized version that happens to avoid every edge the real parser touches.
3. **Run the new test and show the literal pass/fail output** - not "should work," not "the
   logic is correct," not a description of what the test checks. The actual `pytest` (or
   equivalent) output, uncut.
4. **Run the full existing regression suite**, not a hand-picked subset chosen because it's
   known to pass. If a subset is run for speed, say explicitly which tests were skipped and
   why, and note that this is not the full picture yet.
5. **State pass/fail counts precisely - never "PASS" as a bare word repeated.** "51 passed, 5
   failed" is a report. "PASS PASS PASS" is not - it conveys no information about what was
   actually checked and invites exactly the false confidence this protocol exists to prevent.
6. **If anything fails, say so before proposing next steps** - do not silently retry until
   green, do not narrow the test until it passes, do not report the failure as "unrelated"
   without showing the evidence that it predates this change (e.g. the same failure occurs on
   the pre-change code too).
7. **Never say "fully cut over," "done," "live," or "verified" without the run output
   directly supporting that claim.** If verification was partial (only imports checked, only
   a subset run, only the old code path tested), say exactly what was and wasn't checked -
   "imports cleanly, not yet run against real data" is honest and useful; "fully cut over" when
   the live class was never executed once is not.

## The specific failure pattern to never repeat

Testing class A while class B is what's actually running in production, then reporting the
result as if it validates B. Before claiming any test "confirms the Brain is parsing the
payload correctly" (or equivalent), grep for where the class under test is actually
constructed in the composition root and confirm the test targets that exact class by name.
