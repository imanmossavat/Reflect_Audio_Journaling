# REFLECT Project — Implementation Contract (Document B)

**This document governs mechanism.** It is the single source of truth for what
gets built. Its companion, `REFLECT_Design_Document.pdf` / `.md` (Document A),
governs intent and rationale — every section below that needs justifying
points back to a specific section there rather than re-arguing it here.

**Precedence rule:** Document A wins on intent. This document wins on
implementation detail. If this contract ever produces behavior that
contradicts a principle in Document A, that is a bug in this contract to fix,
not a tradeoff to negotiate turn by turn.

**Self-contained for the build:** a plain-text/markdown export of Document A
ships alongside this file (`REFLECT_Design_Document.md`) for environments
without PDF extraction available. If the two diverge, the PDF is canonical.

**Superseded by this document:** `chatbot_baseline_design_ollama.md`,
`developer_guide_graceful_turns.md`, `student_guide_difficult_turns.md`, the
gap report, and the earlier `reflection_loop_contract.md` draft. Their content
has been triaged into this document, into Document A, or explicitly dropped
(stage machinery — see §9). They should be marked superseded wherever they
live, not treated as live reference.

**Anti-regression rule:** if a deleted concept reappears in another form — an
implicit stage baked into prompt wording, a hidden fact ledger reconstructed
inside a helper function, history replay smuggled back in for "robustness" —
treat it as a regression bug, not an acceptable variant.

---

## 1. Scope

**In scope:** the per-turn conversational loop — Ask, Update, and the
persistence and retrieval that support them.

**Out of scope for this build** (see Document A §10 — both are open
decisions, not oversights):
- Advisor-facing view / correction interface
- Closing artifact / final document generation

Do not build placeholder scaffolding for either. If Document A §10 resolves
one of them into scope, that's a new section of this contract, not an
extension of an existing stub.

---

## 2. The four objects, and where `reflection_state` does and doesn't exist

See Document A §6 for what these objects are and why.

**Scope of the table — resolved.** `talk_it_through` is a `Focus` *value*
inside the structured flow: it shares `reflection_state` like any other
Focus, and Gist/Open Thread keep updating normally under it. This is
different from the pre-existing free-chat RAG path (`/query-stream`), which
runs on its own `chat_id` and is a separate flow entirely — it never creates
or touches a `reflection_state` row, not even an unused one. So:
**`reflection_state` exists only for chat_ids that are in the structured
reflection flow.** A RAG-only chat has no row in this table at all.

```ts
type SourceUnit = {
  source_id: string;
  unit_id: string;        // stable within the source — paragraph index for
                           // typed entries, WhisperX segment id for audio
  text: string;
};

type Focus = {
  value: "explore_why" | "decide_next" | "talk_it_through" | string;
  set_by: "student";       // never set by the model
  set_at_turn: number;
};

type Gist = {
  text: string;             // one paragraph, regenerated each turn
  citations: { source_id: string; unit_id: string }[]; // every retained
                           // claim must trace to at least one of these
};

type OpenThread = {
  text: string | null;      // null only at session start, see §3
  source_ref: { source_id: string; unit_id: string } | null;
};

type ReflectionState = {
  chat_id: string;          // reuse the existing chat/session identifier,
                           // do not introduce a new session_id; only created
                           // for chats in the structured flow (see above)
  sources: SourceUnit[];    // selected this session
  focus: Focus;
  gist: Gist;
  open_thread: OpenThread;
  updated_at: string;
};
```

One row per `chat_id`. Upserted on every Update. Not versioned — see §7 if
you want a debugging history, which is a separate, optional log, not part of
this live row.

---

## 3. Session initialization (turn 1 has no prior state)

At session creation, before any message is sent:

- The student selects Sources (as today).
- The student picks an initial **Focus** explicitly. There is no guessed or
  defaulted Focus — the picker is part of session start, not optional.
- `Gist` seeds as `{ text: "", citations: [] }`.
- `Open Thread` seeds as `null`.

Ask gets an explicit branch for this case (folded into §5's response rules):
if Gist is empty and Open Thread is null, treat this as session start — open
with one question grounded in whichever retrieved Source units are most
relevant to the chosen Focus, rather than treating empty state as malformed
input. Update runs normally after the first exchange like any other turn.

---

## 4. Turn loop

```
INPUT: chat_id, student's new message

→ RETRIEVE (vector similarity over ChromaDB, unit-level index — see §8)
    query: embed(open_thread.text + new message)
            — on turn 1, open_thread.text is null; embed Focus + new
              message instead
    return: top 3–5 SourceUnits by similarity
    cap: combined retrieved text ≤ 250 tokens (see §5 budget table)

→ ASK (generation call)
    sees: retrieved Source units + Focus + Gist + Open Thread + message
    produces: facilitator reply, streamed, with inline citation tokens
      (format in §5) for any claim about what the student wrote or
      experienced
    must follow: difficult-turn handling, epistemic-agency constraint,
      one-question-per-turn rule — all in §5

→ THIN-TURN GATE (code, before Update)
    if message is thin (see §6 for definition):
      skip Update entirely
      Gist and Open Thread unchanged
      reply from ASK still goes through
      → end turn here

→ UPDATE (extraction call)
    sees: prior Gist + prior Open Thread + the exchange that just happened
      (student message + facilitator reply) + the retrieved Source units
      Ask was given
    produces (strict JSON):
      - new Gist { text, citations }     — see §6 for the drift-mitigation
        rule governing how this is regenerated
      - Open Thread: { settled: bool, next: string|null, source_ref }
      - focus_shift_suggested: string | null   — never auto-applied (§6)
    on parse/validation failure:
      keep prior Gist and Open Thread unchanged
      reply from ASK still goes through
      log failure (§10), no retry
```

Note on call count: this is three model-adjacent calls per substantive turn
(retrieval embedding + Ask + Update), not the two-call budget the original
baseline doc aimed for. That's a deliberate tradeoff, not an oversight —
named here so it isn't rediscovered as a surprise later.

---

## 5. Generation prompt assembly (Ask)

Slot order matters — put role/instructions at the start and end, variable
content in the middle, because models attend more reliably to the start and
end of a prompt than the middle.

```
[role / policy — short, ~150 tokens]
[current focus, stated plainly — ~30 tokens]
[gist — one paragraph, or "no conversation yet" on turn 1 — ~150 tokens]
[open thread — one sentence with its source reference, or "none yet — this
  is the opening turn" — ~50 tokens]
[retrieved source units relevant to the open thread / new message —
  cap 250 tokens total across all units]
[student's new message — omitted on turn 1 if Ask opens the conversation —
  ~150 tokens]
[response rules — see below — ~150 tokens]
```

Total budget: stay under ~1,000 tokens for the assembled prompt excluding the
student's message history (there is none — Gist is the only continuity
device; no transcript, no turn window).

**Citation format — resolved.** Inline token embedded directly in the
streamed reply text, at the point of reference: `{{source_id:unit_id}}`,
e.g. `{{src1:p3}}`. This is deliberately not a separate JSON field — the app
already streams Ask's reply via SSE, and wrapping the output in JSON would
break that. Frontend strips the token via
`/\{\{([\w-]+):([\w-]+)\}\}/g` and renders a link/chip in its place.
Citation presence in free text cannot be hard-validated the way Update's
JSON output can; treat repeated absence of citations on claims about source
content as a prompt-tuning signal via the failure log (§10), not a per-turn
validation failure.

**Response rules — carried forward from the prior developer guide
near-verbatim, they were already correct and were dropped in an earlier
draft of this contract:**

```
Normal turn:
- Ask exactly one focused question.
- Use the student's own words when referencing what they said.
- Never label an emotion, motive, or interpretation the student did not
  state. This is a hard constraint, not stage-specific — see Document A
  §7, "words in the student's mouth."
- If you reference something the student wrote, cite it inline as
  {{source_id:unit_id}}.
- Maximum 120 words.

If this is the opening turn (Gist empty, Open Thread null):
  Open with one question grounded in the retrieved source units most
  relevant to the student's chosen Focus. Do not ask the student to
  restate what's already in the sources.

If the student's message is very short or unclear:
  Do not guess at meaning. Ask one open question to invite more.
  e.g. "Can you tell me a bit more about that?"

If the student seems to be going off-topic:
  Acknowledge briefly in one clause, then return to the open thread.
  e.g. "That's worth noting — coming back to [open thread]..."

If the student expresses resistance or says they don't know:
  Do not push. Offer a simpler, more concrete version of the question.
  e.g. "That's okay — what's one thing you remember clearly about that?"

Never repeat a question that has already been asked and answered, even
briefly. If a question didn't land, try a different angle next turn.

If in doubt: ask the simplest possible question and wait.
```

The model should not be aware that an architecture, a pipeline, or prior
stages exist at all — it sees only the slots above.

---

## 6. Extraction prompt assembly (Update)

```
[prior gist + prior open thread — light orientation only, see drift rule
  below]
[the exchange that just happened: student message + facilitator reply,
  including its inline citation tokens]
[the source units Ask was given]
[instruction — see below]
```

**Gist drift mitigation (this is the important part — see Document A §7):**
a rolling summary written from its own prior version, turn after turn,
compounds distortion. To prevent that:

- Every sentence in the new Gist must carry at least one `citation` pointing
  to a Source unit, or be directly attributable to something the student
  said in the current exchange (not to the model's prior synthesis of it).
- A sentence carried forward from the previous Gist that no longer has a
  traceable citation gets dropped during regeneration, not silently kept.
- Regenerate Gist primarily from the source units and the current exchange;
  use the prior Gist only as light orientation for what's already been
  covered, not as the thing being incrementally edited.
- Update's citations array is generated independently of whatever inline
  tokens Ask happened to emit — it is not required to reuse Ask's exact
  citations, only to ground its own.

**Open Thread:**
- If `settled: true`, the next Open Thread must be grounded in a source unit
  or in something new the student just said — never invented from the
  model's own sense that "this would be a good next question."
- Replace, do not append. There is never more than one Open Thread.
- No numeric threshold defines "settled" (deliberately — see the closing
  note on this in the prior round of review). This is left to model
  judgment in the prompt, the same way the old keyword/count thresholds were
  removed elsewhere. It means this behavior can't be unit-tested the way the
  old stage gates could; that's a known, accepted tradeoff, not an oversight.

**Focus shift:**
- `focus_shift_suggested` is a string the UI can surface to the student as a
  suggestion. It never changes `Focus.value` directly. Only the student
  changes Focus.

**Output schema (strict JSON, no markdown fences, no preamble):**

```json
{
  "gist": { "text": "string", "citations": [{"source_id": "string", "unit_id": "string"}] },
  "open_thread": { "settled": false, "next": "string or null", "source_ref": {"source_id": "string", "unit_id": "string"} },
  "focus_shift_suggested": "string or null"
}
```

**Parsing:** strip markdown fences if present despite instructions, then
`json.loads` and validate against the schema (Pydantic or equivalent). On
`JSONDecodeError` or validation failure: discard the entire response, keep
prior state, log the raw response and error (§10), do not retry.

---

## 7. Thin-turn gate

Reuse the existing definition and rationale — this was already correct:

```python
THIN_RESPONSES = {
    "ok", "yes", "no", "maybe", "idk", "i don't know", "not sure",
    "nothing", "fine", "sure", "hmm", "yeah", "nope", "don't know",
    "no idea", "i guess", "alright", "whatever", "i don't care"
}

def is_thin_turn(user_message: str) -> bool:
    cleaned = user_message.strip().lower().rstrip(".,!?")
    if cleaned in THIN_RESPONSES:
        return True
    if len(user_message.strip().split()) <= 3:
        return True
    return False
```

A three-word message can occasionally contain real information, but the cost
of skipping Update on it is low — Ask's "very short or unclear" handling
asks a follow-up, and the next turn captures it.

---

## 8. Persistence and retrieval infrastructure

- **`reflection_state` table** — one row per qualifying `chat_id` as defined
  in §2. Upsert on every Update. Reuse the chat/session identifier already
  in the system; do not introduce a parallel `session_id`.
- **Source chunking** — new work, not a refactor of existing code:
  - Typed entries: split on paragraph (blank-line) boundaries at ingest
    time, assign sequential ids (`src1-p3`).
  - Audio entries: reuse existing WhisperX alignment segments as the unit
    boundaries — this is exposing IDs that already exist, not deriving new
    ones.
  - Store as a `units` JSON column on the existing source row (derived data
    tied 1:1 to the source — does not need its own relational identity).
- **Citation rendering** — new frontend work: parse the `{{source_id:unit_id}}`
  token (§5) out of streamed text and render it as a link back to that
  unit's location in the source viewer.
- **Retrieval — corrected, this is new infrastructure, not reuse.** The
  existing ChromaDB setup indexes one embedding per whole source, used by
  the separate RAG path. The RETRIEVE step in §4 needs one embedding **per
  unit** so it can return SourceUnit-level matches, not whole-document
  matches. Concretely:
  - For newly ingested sources, compute one embedding per unit at the same
    pass that does the chunking above — this is additional work in that
    pass, not a second pipeline.
  - For sources already indexed under the old whole-source scheme, this
    requires a one-time backfill job (re-chunk + re-embed existing sources)
    before unit-level retrieval will work for them. Scope this explicitly
    as a migration task, not an assumed side effect of shipping the chunker.
  - Vector metadata per embedding: `{source_id, unit_id, chat_id}`.
  - Query: embed `open_thread.text + new message` (or Focus + message on
    turn 1), retrieve top 3–5 units, enforce the 250-token combined cap
    from §5 before injection.

---

## 9. Hard deletions

Remove entirely, do not "clean up":

- transcript / history-window replay in the generation prompt
- `step` counter as a gating mechanism (frontend or backend)
- stage completion keyword-matching logic
- advance-confirmation substring matching
- any versioned `state_v{n}.json` file writes
- full-journal-text injection (replaced by retrieved, addressed source
  units, scoped per §5's budget)
- any fact ledger / facts list, append-only or otherwise

---

## 10. Failure handling and logging

| Situation | Behavior |
|---|---|
| Update returns malformed JSON / fails validation | Keep prior `gist` and `open_thread` unchanged. Ask's reply still goes through. Log raw response + error. No retry. |
| Thin turn | Skip Update entirely. State unchanged. Ask's reply still goes through. |
| Retrieval returns zero relevant units | Ask proceeds with Focus + Gist + Open Thread only, no source units this turn. Not an error. |
| Ask's reply contains a substantive claim with no citation token | Not blocked or retried. Logged for prompt-tuning review (§5). |

```python
def log_extraction_failure(user_message: str, raw_response: str) -> None:
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_message": user_message[:200],
        "raw_response": raw_response[:500],
    }
    with FAILURE_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")
```

Review this log during development. Repeated failures of the same shape mean
the extraction prompt needs adjustment — fix the prompt, not the runtime
retry behavior.

---

## 11. Definition of done

Not feature parity with any prior spec. Instead:

> A 10–15 turn conversation stays grounded in the selected sources — every
> substantive claim in a facilitator reply or in Gist is traceable to a
> Source unit or the current exchange — does not repeat itself, handles a
> short answer / off-topic remark / resistance without forcing the
> conversation forward, and lets the student redirect Focus without the
> system losing track of where it was.

---

## 12. Out of scope — explicit

Per Document A §10, until resolved there:

- No advisor view, no advisor-facing read or write path into
  `reflection_state`.
- No closing-artifact generation call. The loop in §4 is the entire scope
  of this build.

---

## 13. Remaining open question

- Whether `Focus.value` needs to be rendered persistently in the UI, or only
  implicitly shapes how Ask phrases things. Everything else previously
  listed here has been resolved into the sections above.
