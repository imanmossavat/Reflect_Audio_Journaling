# Stateful eval — iteration log

Running log of what we changed and what each run revealed. **Newest first.** One entry per
change/run. Keep it factual: what changed, the run id + headline metrics, the finding, the next step.

Datasets: `baseline` (Maya, easy/single-note) · `stateful` (Niels, state-evolution, multi-hop).
Read alongside `GUIDE.md` (why the harness is built this way) and `README.md` (how to run).

---

## 2026-06-08 — reranker ON vs OFF (`130136Z` = OFF) is a wash; generator masks all retrieval signal

**Config:** reranker **OFF** · embed `nomic-embed-text` · chat `gemma4:26b` · top_k 5 · **old prompt**.
Re-run of the OFF arm lost to the `103914Z` same-second collision. Its retrieval numbers came back
**byte-identical** to the clobbered run (P@5 0.3733 / R@5 0.6595 / MRR 0.7244) — confirms the lost first
printout *was* the OFF arm, and that embedding+no-rerank retrieval is deterministic.

**OFF vs ON (`103914Z`), both old prompt:**

| metric | OFF `130136Z` | ON `103914Z` |
|---|---|---|
| P@5 / R@5 / MRR | 0.3733 / 0.6595 / 0.7244 | 0.36 / 0.6571 / 0.7133 |
| context_recall | 0.9333 | 1.0 |
| refusals_no_context | 1 | 0 |
| **answer_accuracy** | **0.4667 (7/15)** | **0.4667 (7/15)** |
| incorrect_refusals / partial | 5 / 2 | 5 / 2 |

**Finding:** the reranker rescues exactly one question from zero-gold context (context_recall
0.933→1.0), at a hair of P@5/MRR cost elsewhere — but the generator **refuses that rescued question
anyway**, so it just shifts `refusal_no_context`→`incorrect_refusal`. Net accuracy is **identical**.
The reranker cannot demonstrate value while the generator won't answer on context it already holds.
Combined with "26B = e4b on refusals", three levers (model size, reranker on/off) all leave accuracy
pinned at 0.467 → **the `TEXT_QA_TEMPLATE` refusal clause is the sole bottleneck.**

**Next:** edit the refusal clause, then re-run **both** arms on the new prompt (current comparison is the
old-prompt baseline). Only after the generator commits can reranker/model-size effects be measured.

---

## 2026-06-08 — `stateful` run `20260608T103914Z_9aed6bc7`: 26B does NOT fix over-refusal; prompt is the culprit

**Config:** reranker ON · embed `nomic-embed-text` · chat `gemma4:26b` · top_k 5.
**Summary:** P@5 0.36 · R@5 0.657 · MRR 0.713 · answer_accuracy **0.467** (7/15) ·
5 INCORRECT_REFUSAL · 1 WRONG_OTHER · 2 PARTIAL · 3 CORRECT_REFUSAL.

**Headline:** upgrading e4b (4B) → 26B bought ~nothing on false refusals. `…083857Z` (e4b) had 5
incorrect refusals; this 26B run *also* has 5 (ST05/06/10/11/12). **ST06 refused on rank-1 evidence**
(S-022 "we're going to try again" at position 1). Capacity isn't the floor — the `TEXT_QA_TEMPLATE`
refusal clause is. This is the change to make next, not a bigger model.

**Failure split (revises the earlier "retrieval is healthy" claim):**
- *Generation-bound (evidence was in context, model still failed):* ST06 (refused, rank-1), ST10
  (employer+offer retrieved, refused), ST09 (S-030 "archived" at rank 2, still reported project active
  → WRONG_OTHER, stale-state).
- *Retrieval-bound (a required gold note never made top-5):* ST05 (missing S-025), ST11 (missing S-029),
  ST12 (missing S-009/S-020). Plus ST13/ST15 need **7 gold notes each** but top_k=5 caps them → forced PARTIAL.
- **New observation:** on the multi-hop/temporal Qs the reranker scores collapse to a flat ~0.15 floor
  (ST12, ST15 all five tied at .150x) — *zero* ranking signal exactly where the dataset is hard. It only
  fires on simple single-entity lookups (ST03 S-031→1.12, ST08 S-011→0.84). nomic-embed-text isn't
  separating this short-journal corpus.

**Collision caveat:** this folder shares stamp `103914Z` with its intended reranker-OFF sibling — both
ran in the same UTC second, `_make_run_dir`'s `mkdir(exist_ok=True)` + mode-`w` writes clobbered the OFF
arm into this one. **Surviving data = reranker ON** (config.json reranker:true). The OFF arm is lost.
TODO: add a uniquifier/suffix to `_make_run_dir` so same-second launches get distinct folders.

**Perf:** `gemma4:26b` runs **49% CPU offload** with **num_ctx 262144** (`ollama ps`) → ~8 min/question,
~2.5 h/run. The 256K context reserves VRAM that forces the CPU spill. Drop num_ctx to 4–8K, or use a
model that fits fully in VRAM (e.g. `gpt-oss:20b`, 13 GB).

**Next:** (1) reranker-OFF re-run in progress as `20260608T130136Z_9aed6bc7` — **still uses the OLD
prompt**, so when comparing arms don't attribute a prompt delta to the reranker. (2) Edit the refusal
clause in `TEXT_QA_TEMPLATE` (`Backend/app/services/rag.py`), then re-run reranker-ON. (3) `_make_run_dir`
uniquifier. (4) Bump top_k for the aggregation Qs (ST13/ST15 are capped at 5).

---

## 2026-06-08 — harness: state-aware answer scorer added to `metrics.py`

**Change:** `harness/metrics.py` now scores the *answer*, not just retrieval. Per question it emits a
label: CORRECT · PARTIAL · **INCORRECT_REFUSAL** (refused but a gold note was retrieved) ·
REFUSAL_NO_CONTEXT (refused, nothing retrieved) · **WRONG_STATE** (named a competing value of the
same state variable, e.g. the current job when 'former' was asked) · WRONG_OTHER · CORRECT_REFUSAL ·
FAILED_REFUSAL. Multi-part answers (`state_role` with `+`/`mixed`/`full_history`) need *all* alias
parts → else PARTIAL. WRONG_STATE uses `world_state.json` to know the competing values. `run_eval.py`
now writes `answers.csv` and folds answer metrics into `summary.csv` every run.

**Re-scored `…083857Z`:** answer_accuracy **0.467** — 7 CORRECT · 5 INCORRECT_REFUSAL · 3 CORRECT_REFUSAL
· 3 PARTIAL · 0 WRONG_STATE (the model *refused* rather than asserting wrong states). By trap_type:
recency_trap 1/1, recency_ok 2/2, salience_trap 1/2. This replaces the earlier lenient hand-count
(~9–10/15) with an honest 7/15 — the 3 PARTIALs were multi-part answers covering only some parts.

**Verified WRONG_STATE fires** (synthetic ST07, expected Meridian): "Polder" (newest) → WRONG_STATE,
competing employer → WRONG_STATE, "Meridian" → CORRECT, unrelated → WRONG_OTHER. Exactly the
"took the newest note as truth" failure the stateful set targets.

**Limitation:** scoring is alias substring matching. A garbled answer that still contains the right
keyword (ST09: temporally inverted but says "archived") scores CORRECT. Catching that needs an
LLM-judge or a stricter answer template — deferred.

**Next:** re-run with a stronger chat model; the false refusals should clear and WRONG_STATE should
start firing on the recency/salience traps (where the real state-reasoning signal lives).

---

## 2026-06-08 — `stateful` run `20260608T083857Z_9aed6bc7`: generation is the bottleneck, not retrieval

**Config:** reranker ON · embed `nomic-embed-text` · chat `gemma4:e4b` · top_k 5.
**Summary:** P@5 0.36 · R@5 0.657 · MRR 0.713 · **context_recall 1.0** · unanswerable_idk_rate 1.0.

**Finding — retrieval is healthy, the generator is the floor.**
- Every answerable question retrieved ≥1 gold note (context_recall = 1.0). **Zero** failures were
  retrieval misses.
- ~9/15 answer accuracy, and **every failure was generation-side**:
  - **5 incorrect refusals** — model said "I don't know" with the answer in the retrieved context:
    ST02 (Saffron present), ST05 (Bright Harbor present), ST06 (Priya present), ST10, ST11.
    ST02 is the smoking gun: single-hop, gold retrieved, literal "Calling it Saffron" in context, still refused.
  - **1 garbled temporal synthesis** — ST09 asked *current* Saffron status (abandoned); model recited a
    temporally **inverted** history ("archived… however later opened again") and never said abandoned.
- One clean positive: **ST07 (`recency_trap`) correct** — "where did I work *before* my current job" →
  *Meridian* (the older state), not the newest note (Polder). So ranking surfaced the right evidence.

**Implication:** state-awareness (current/former/prospective) is **not yet measurable** — the generator
won't answer the easy questions, so it masks the signal. `gemma4:e4b` (4B-class) over-applies the
QA prompt's "else say I don't know" clause.

**Next:** (1) re-run with a stronger chat model — highest-value change. (2) Inspect/loosen the refusal
clause in `TEXT_QA_TEMPLATE` (`Backend/app/services/rag.py`). (3) State-aware scorer in `metrics.py`
must flag *incorrect-refusal* and *wrong-state* — a plain alias substring match over-credited ST09.

---

## 2026-06-08 — `stateful` questions rewritten to first person

**Change:** questions phrased about the user, not the persona: "Where does Niels work?" → **"Where do
I work now?"** etc. (the app is a personal journal — the user asks about *themselves*).
**Why:** matches real query distribution; "Niels" never appears in a real user's question.
**Note:** run `…083857Z` predates this; its stored `raw.jsonl` still shows ST02's old "…**he** was
building?" phrasing. The live `questions.json` is already first-person — re-run to pick it up.

---

## Template for new entries

```
## YYYY-MM-DD — <dataset> run <run_id> (or: <change title>)

**Config:** reranker on/off · embed <model> · chat <model> · top_k N.
**Summary:** P@K .. · R@K .. · MRR .. · context_recall .. · idk_rate ..
**Finding:** what the numbers + a look at raw.csv actually show (retrieval vs generation; which Qs; why).
**Next:** the single highest-value change to try.
```
