# REFLECT — Minimal Human-Enforced Binding Layer

Every other artifact in this repository's operating system (`CLAUDE.md`,
`INVARIANTS.md`, `DO_NOT_TOUCH.md`, `ENFORCEMENT_MAP.md`,
`TEST_STRATEGY.md`, `RUNTIME_GUARDS.md`, `CHANGE_IMPACT_RULE.md`) is
currently **non-binding**. Nothing forces anyone to read them. This
document is the only part of the system that depends on nothing except a
person choosing to follow it — so it has to be short enough to actually
survive time pressure, or it's worthless.

## Part 1 — Human binding mechanism

### Change justification format (write this, don't just think it)

Before the first edit, in whatever form you're already using to track
the change (commit message draft, PR description, scratch note — doesn't
matter where, only that it exists before code changes):

```
Area touched:        [reflection loop / ingestion / generation_registry /
                       SSE streaming / reflection_state / retrieval]
Invariant IDs at risk: [from INVARIANTS.md / DO_NOT_TOUCH.md, or
                       "none identified"]
Multi-session exposure: [does this path run per-request, could two
                       requests hit it for the same chat_id/source_id
                       at once? yes / no / unsure]
Existing detector:    [name one from TEST_STRATEGY.md /
                       RUNTIME_GUARDS.md, or "none"]
```

After the change, before calling it done:

```
Not verified:         [explicit list of what you did NOT test — this
                       line may not be left blank]
Manual check performed: [what you actually ran and observed]
New silent-failure surface: [state explicitly, even if "none identified"]
```

Six lines before, three after. This is the whole mechanism. It works
only because it forces the two moments people skip under pressure —
naming what's at risk before touching code, and admitting what's
unverified after — into something written down instead of assumed.

### Per-area minimum check (before editing)

- **Reflection loop**: does this touch the read → generate → write
  sequence around `ReflectionState`? If yes, R1 applies —
  `generation_lock` does not protect this path (see `DO_NOT_TOUCH.md`).
- **Ingestion pipeline**: does this merge two pipeline-stage sessions, or
  does a new delete/reprocess path skip deleting either the SQL rows or
  the Chroma vectors?
- **`generation_registry`**: does any new path write `reflection_state`
  after generating a reply? It must be isolated in its own try/except.
  Does it add a new Ollama/guard call site not already accounted for in
  `generation_lock`'s scope?
- **SSE streaming**: does every path through the job lifecycle still emit
  exactly one terminal event? Does anything assume the job registry
  survives a restart?
- **`reflection_state` logic**: does anything assume `updated_at` (or any
  field) provides concurrency protection? It doesn't, anywhere, today.
- **Retrieval logic**: does every new Chroma query set or check the
  unit/chunk kind filter?

### What must never be skipped, even under deadline pressure

- The "Not verified" line. Confidence is exactly the condition under
  which R1/R5/R11-class bugs ship — they pass every normal single-session
  test by construction. Skipping this line is how they get through.
- Actually running two overlapping requests by hand when touching
  `reflection_state` — two tabs, two `curl` calls close together,
  whatever's fastest. A single-request test cannot reveal this class of
  bug regardless of how carefully it's written.
- Checking `DO_NOT_TOUCH.md` specifically when a change "looks like a
  small cleanup." That framing is precisely how forbidden refactors get
  through — nobody sets out to violate an invariant, they set out to tidy
  something up.

## Part 2 — Failure before merge (manual model, no tooling)

| Risk | How a human would notice | Observable symptom | Caught when | Why it's easy to miss |
|---|---|---|---|---|
| **`reflection_state` race** (R1) | Only by deliberately firing two overlapping requests at the same `chat_id` and diffing the row before/after | Gist/Open Thread reverts, or the reflection appears to "forget" something just said — no error anywhere | Only *after* the run, only if someone specifically tests multi-session behavior | This is a local-first, nominally single-user app — multi-session testing isn't the default instinct, and the bug is timing-dependent, so even a deliberate test can pass by luck |
| **Route-level blind spots** (R11) | Only by exercising the actual endpoint through the running app or a manual HTTP client — reading the route code doesn't reveal a broken status code or malformed SSE frame | A stream that hangs, an SSE event the frontend silently fails to parse, a stuck loading skeleton | Only *during* a run, never before commit (nothing asserts route behavior today) | Already proven insufficient once — the last batch of route-layer bugs was found by live testing, not review, meaning "read the diff" has already been shown not to catch this class |
| **Ingestion inconsistency** (R5 delete pairing / R6 session splitting) | For deletion: search for content that should be gone after a reprocess/delete. For sessions: notice the whole app stalling specifically during a long transcription/LLM step | Deleted content still retrievable via RAG; or unrelated requests hang while ingest runs | Deletion gap: *after* run, and only if someone tests for absence, not just presence. Session gap: *during* run, but easy to attribute to something else | Testing a "delete" or "reprocess" feature naturally checks that new content appears, not that old content is gone — a classic untested-negative-case gap. Stalling reads as "the app is just slow," not as a specific regression |
| **SSE lifecycle loss** (R7) | Restart or hot-reload the backend while a generation is actively streaming, then watch whether the frontend recovers or hangs | Streaming skeleton/spinner never resolves — no error, no completion, just stuck | *During* run — and ironically likely to be seen constantly during normal local development | Developers restart their own backend constantly while iterating and mentally file the resulting stuck UI under "dev-mode noise," not "this would also happen on a production crash" |

All four rows share one property: nothing about them fails loudly. Each
one requires a human to go looking for the *absence* of a correct
behavior, not just the presence of an incorrect one — which is
structurally the kind of check people skip first when rushed.

## Part 3 — Governance stack (honest reality model)

| Layer | Contents | What it guarantees *today* |
|---|---|---|
| **Policy** | `CLAUDE.md`, `DO_NOT_TOUCH.md` | Nothing automatically. Guarantees only that the rule exists and is findable *if* someone opens the file before editing. Pull-based, not push-based. |
| **Detection thinking** | `INVARIANTS.md`, `TEST_STRATEGY.md` | Nothing runtime. `TEST_STRATEGY.md` is explicitly unimplemented — this layer guarantees the failure modes are named and prioritized, not that any of them are caught. |
| **Runtime safety** | `RUNTIME_GUARDS.md` | Nothing yet — it's a proposal, not code. Even fully implemented, several guards are designed to *log* rather than hard-fail (deliberately, to avoid an availability regression), so this layer's ceiling is "visible after the fact to someone watching logs," not "prevented." |

**What none of the three layers guarantee, at any point:**

- That anyone reads them before making a change. There is no push
  mechanism anywhere in this stack — every layer requires the developer
  to go looking.
- That a violation is caught before a user sees it. Even at full
  implementation, the best this stack does for several invariants is
  "log it and continue," which means *detection* here does not mean
  *prevention*.
- That the documents stay accurate. Nothing checks these files against
  the code over time — this repository's own general developer handbook
  already drifted from the reflection-loop rebuild once; there's no
  reason to expect these files are exempt from the same decay.

**Where failure can still silently occur, stated plainly:** today, with
`TEST_STRATEGY.md` and `RUNTIME_GUARDS.md` both unimplemented, every P0
risk in `INVARIANTS.md` can be violated by an ordinary, well-intentioned
change and ship with zero warning at any layer. This entire operating
system currently has the enforcement power of a comment: real if
habitually respected, worthless the moment someone is in a hurry and
doesn't open the file. The only thing standing between a silent P0
violation and production, right now, is whether the specific person (or
Claude session) making the change happens to follow Part 1 of this
document without being told to. That is not yet a governance system —
it's a well-organized set of intentions with one thin, human-dependent
layer underneath it.
