# REFLECT — Reality Check Brief

Purpose: the governance stack (`CLAUDE.md`, `INVARIANTS.md`,
`DO_NOT_TOUCH.md`, `ENFORCEMENT_MAP.md`, `TEST_STRATEGY.md`,
`RUNTIME_GUARDS.md`, `HUMAN_PROCESS.md`) is currently unenforced — it's
documentation, not tooling. Nothing in it has been verified against the
running app. This is not a doc-review task — don't just read the code and
say whether it looks right. Run each item below against the live app (or
a real HTTP client) and record what actually happens. These are silent
failure modes by design: no exception, no failed test, no error log. The
only way to catch them is to go looking for the absence of correct
behavior.

Fill in the "Observed" and "Verdict" fields for each item and hand the
whole file back.

---

## 1 — `reflection_state` race (R1)

**Setup:** two overlapping requests against the same `chat_id` — two
browser tabs, or two `curl`/HTTP calls fired close together.

**Steps:**
1. Open the same chat in two tabs (or prep two near-simultaneous manual
   requests hitting the same `chat_id`).
2. Trigger a reflection turn in both at roughly the same time.
3. Inspect `reflection_state` for that `chat_id` before and after — does
   it reflect both updates, or did one silently overwrite the other?

**Symptom to watch for:** Gist/Open Thread appears to "revert" or forget
something just said, with no error anywhere.

**Observed:**

**Verdict:** [confirmed silent overwrite / serialized correctly / inconclusive]

---

## 2 — Route-layer blind spots (R11)

**Setup:** a real HTTP client (browser network tab, `curl`, or Postman)
against `/generate-question`, `/query-stream`, and
`/chats/{id}/generation-stream`. Reading the route code does not count —
this has to be exercised live.

**Steps:**
1. Hit each of the three endpoints through normal app usage.
2. Watch for bad/unexpected status codes, malformed or out-of-order SSE
   frames, and error paths (e.g. bad input, guard block, empty source).
3. Note anything the frontend silently fails to parse (stuck loading
   skeleton with no console error is the classic tell).

**Observed:**

**Verdict:** [issues found — list them / clean / inconclusive]

---

## 3 — Ingestion delete pairing + session splitting (R5 / R6)

**Setup:** a source you can safely delete or reprocess.

**Steps:**
1. Note some distinctive content in the source (a phrase you can search
   for).
2. Delete or reprocess the source.
3. Search/RAG-query for that content afterward — confirm it's actually
   gone from retrieval, not just from the source list UI.
4. Separately: kick off a long transcription or LLM-heavy ingest, and
   while it's running, try an unrelated request (e.g. open a different
   chat, hit another route). Does the unrelated request stall?

**Symptom to watch for:** content still retrievable via RAG after
delete/reprocess (Chroma vector orphaned); or the whole app appearing to
freeze during ingestion (shared DB session/transaction).

**Observed:**

**Verdict:** [orphaned vectors found / clean — deletion; stalled / clean — session]

---

## 4 — SSE lifecycle loss on restart (R7)

**Setup:** ability to restart or hot-reload the backend process.

**Steps:**
1. Start a generation that streams via SSE.
2. While it's actively streaming, restart/kill the backend.
3. Watch the frontend: does it recover to a well-defined state (e.g.
   `idle`), or does the streaming skeleton/spinner hang forever with no
   error?

**Observed:**

**Verdict:** [hangs / recovers cleanly / inconclusive]

---

## 5 — Doc-drift spot check

**Setup:** none — this is a code-vs-doc comparison, not a live test.

**Steps:** Pick 3-4 claims from `INVARIANTS.md` or `DO_NOT_TOUCH.md` that
name a specific file, function, or behavior, and confirm each still
matches current code. `HUMAN_PROCESS.md` explicitly admits these docs
already drifted from the code once before — this checks whether they've
drifted again since.

**Observed:** [claim → still accurate? y/n, with file:line]

**Verdict:**

---

## Notes for whoever reads this after

- These four risk classes (R1, R11, R5/R6, R7) are the ones named in
  `HUMAN_PROCESS.md` Part 2 as "nothing about them fails loudly." A
  "clean" verdict here means *not reproduced this session*, not *proven
  absent* — these are timing- and state-dependent bugs that can pass by
  luck.
- If anything reproduces, file it in `docs/ISSUES.md` using the existing
  numbering convention (don't renumber existing issues —
  `DO_NOT_TOUCH.md` flags that explicitly) and reference the relevant
  invariant ID (R1/R5/R6/R7/R11) from `INVARIANTS.md`.
