# REFLECT — Change Impact Rule

This is a constraint on process, binding on any Claude session (not a
human checklist). It applies before any edit to: the reflection loop,
the ingestion pipeline, `generation_registry`, SSE streaming,
`reflection_state`'s schema, or retrieval logic.

## The rule

Before writing or editing code in any of the six areas above, answer the
following three questions explicitly, in output the user can see, before
the first file edit:

1. **Which invariant IDs does this change touch?** Cross-reference
   `INVARIANTS.md` and `DO_NOT_TOUCH.md` by ID — not by paraphrase. If
   the change touches an ID with no corresponding line item, say so
   explicitly; do not silently assume it's unaffected.
2. **What silent failure could this introduce — specifically one that
   would pass existing tests?** Loud failures (exceptions, failed tests)
   are not the concern here; `ENFORCEMENT_MAP.md` exists because most of
   the failure modes in this system are silent. If the honest answer is
   "none that I can identify," that claim itself must be stated, not
   omitted.
3. **What test, runtime hook, or logging invariant would detect it?**
   Check `TEST_STRATEGY.md` and `RUNTIME_GUARDS.md` first. If a relevant
   one already exists, name it. If none exists, either add the minimal
   detection mechanism as part of the same change, or state plainly that
   the change is shipping without a detector and why that's acceptable.

## Escalation condition

If question 2 surfaces a plausible silent failure and question 3 cannot
name an existing or newly-added detector for it, do not proceed on
judgment alone — surface the gap to the user and let them decide whether
to accept the risk, request the detector first, or change the approach.
This mirrors the escalation rule in `DO_NOT_TOUCH.md`: these constraints
exist because of concrete prior failures, not default caution, so silent
best-effort is not an acceptable substitute for surfacing the tradeoff.

## What this rule is not

- Not a request for a design review or sign-off — it's a self-check that
  must be visible in-session, not performed silently and then discarded.
- Not a gate on every change in the repository — only the six areas
  listed above, which are exactly the areas `ENFORCEMENT_MAP.md` rates as
  having silent, hard-to-detect failure modes today.
- Not a substitute for `DO_NOT_TOUCH.md` — a change can pass this rule's
  three questions and still be forbidden outright by that list. Check
  both.
