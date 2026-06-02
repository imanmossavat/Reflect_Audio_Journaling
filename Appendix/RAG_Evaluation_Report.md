# RAG Evaluation Report — Maya Synthetic Corpus

**Scope:** Diagnosis of the RAG pipeline against a controlled synthetic journal (Maya world state).

**Evaluation directory:** [Research/RAG/maya_eval/](../Research/RAG/maya_eval/)

---

## 1. Purpose

The goal of this evaluation is to answer, per failing question, *"this went wrong, and in this specific sense"*, so I can prioritize fixes against the actual failure modes the production RAG exhibits.

The eval runs the **real** production RAG (real chat model, real embed model, real `rag.query_sources` path) against an **isolated** Chroma collection, so production embeddings are never touched.

---

## 2. Methodology

### 2.1 Context

- **Source:** Synthetic "Maya" world state lifted from the pipeline doc.
- **Notes:** ~32 short journal-style notes (`notes.json`), each tagged with a stable `note_id`.
- **Generation:** Pre-scripted events expanded into notes by Ollama via [generate_notes.py](../Research/RAG/maya_eval/generate_notes.py).

### 2.2 Questions

- **Total:** 25 questions ([questions.json](../Research/RAG/maya_eval/questions.json))
  - 20 answerable questions from the pipeline doc (single-hop + multi-hop)
  - 5 deliberately unanswerable questions (to measure refusal behavior)
- Each answerable question carries a `gold_supporting_notes` list — the `note_id`s that contain the answer. This is what makes per-question diagnosis possible.

### 2.3 Pipeline

1. [_bootstrap.py](../Research/RAG/maya_eval/_bootstrap.py) — makes use of `app.services.chroma` before any RAG code loads, pointing it at the isolated eval Chroma at `maya_eval/chroma/`.
2. [ingest.py](../Research/RAG/maya_eval/ingest.py) — chunks + indexes notes into the isolated collection `maya_eval_chunks`.
3. [run_eval.py](../Research/RAG/maya_eval/run_eval.py) — runs each question through `rag.query_sources`; writes `results/raw.csv` + `raw.jsonl` (question, expected, generated, retrieved note IDs + scores + texts).
4. [judge.py](../Research/RAG/maya_eval/judge.py) — LLM-as-judge labels each row with a failure mode and rationale.
5. [report.py](../Research/RAG/maya_eval/report.py) — aggregates into the summary below.

### 2.4 Failure-mode taxonomy

| Label | Meaning |
|---|---|
| `CORRECT` | Answer supported, or a proper refusal for unanswerable. |
| `RETRIEVAL_MISS` | None of the gold notes made it into top-k. |
| `PARTIAL_RETRIEVAL` | Some gold notes retrieved; answer missing the rest. |
| `GENERATION_OVERREACH` | Right notes retrieved, but answer over-infers psychology / causality. |
| `GENERATION_HALLUCINATION` | Answer states a fact not in any retrieved chunk. |
| `FAILED_REFUSAL` | Question unanswerable but RAG fabricated an answer. |
| `INCORRECT_REFUSAL` | Answer was in retrieved context but RAG says it is not. |
| `CONTRADICTS_NOTES` | Answer states something the notes explicitly contradict. |

---

## 3. Aggregate Results

**25 questions evaluated.**

| Failure mode | Count | Share |
|---|---:|---:|
| GENERATION_OVERREACH | 12 | 48% |
| CORRECT | 6 | 24% |
| INCORRECT_REFUSAL | 3 | 12% |
| GENERATION_HALLUCINATION | 3 | 12% |
| FAILED_REFUSAL | 1 | 4% |
| RETRIEVAL_MISS | 0 | 0% |
| PARTIAL_RETRIEVAL | 0 | 0% |
| CONTRADICTS_NOTES | 0 | 0% |

### Headline findings

1. **Retrieval is not the bottleneck.** Zero `RETRIEVAL_MISS` / `PARTIAL_RETRIEVAL`. The right chunks consistently make it into top-k.
2. **Generation is the bottleneck.** 16 / 19 non-CORRECT cases (84%) are generation-side: overreach (12), hallucination (3), failed refusal (1).
3. **Overreach dominates** (48% of all questions). The model takes retrieved facts and layers psychological interpretation / second-person framing on top.
4. **Refusal behavior is inverted.** The model refuses 3 questions it should answer (`INCORRECT_REFUSAL`) and answers 1 question it should refuse (`FAILED_REFUSAL`) — the refusal threshold is mis-calibrated, not just biased one direction.
5. **Unanswerable handling is mostly correct** — 5 of 6 `CORRECT` results are the unanswerable bucket. The model is good at refusing when there is genuinely nothing, but bad at deciding which retrieved context is sufficient.

---

## 4. Per-question Results

| # | Failure mode | Question (truncated) |
|---|---|---|
| Q1 | INCORRECT_REFUSAL | Why did Maya delete her message drafts to Lina on May 19? |
| Q2 | CORRECT | What recurring issue affects Maya's physio routine? |
| Q3 | GENERATION_OVERREACH | How is Maya's apartment finances handling related to spreadsheets? |
| Q4 | GENERATION_OVERREACH | Evidence of fragmentation in home maintenance docs? |
| Q5 | GENERATION_OVERREACH | How does Maya's communication with her father reflect uncertainty? |
| Q6 | GENERATION_OVERREACH | Conflicting behaviors re: financial communication with Eva/Tom? |
| Q7 | GENERATION_OVERREACH | What triggers Maya's uncertainty about dentist tasks? |
| Q8 | INCORRECT_REFUSAL | How do Maya's interactions with Lina evolve? |
| Q9 | FAILED_REFUSAL | Relationship between work avoidance and home organization issues? |
| Q10 | GENERATION_HALLUCINATION | Did Maya complete her physio routine on May 17? |
| Q11 | GENERATION_OVERREACH | What did Maya decide about visiting her father after May 15? |
| Q12 | GENERATION_OVERREACH | How does the mortgage spreadsheet use differ from intended? |
| Q13 | GENERATION_OVERREACH | Why did Maya think she'd already sent humidity data to Karel? |
| Q14 | GENERATION_OVERREACH | Email avoidance vs. work communication style? |
| Q15 | GENERATION_OVERREACH | Did Maya confirm father corrected her about the repeated promise? |
| Q16 | INCORRECT_REFUSAL | What caused Maya to stop physio on May 17? |
| Q17 | GENERATION_OVERREACH | Reconciling financial decisions between Eva and Tom? |
| Q18 | GENERATION_OVERREACH | What is unclear about Maya's dental situation? |
| Q19 | GENERATION_HALLUCINATION | Has Maya explicitly completed the mortgage spreadsheet analysis? |
| Q20 | GENERATION_HALLUCINATION | Relationship between Lina's requests and Maya's responses? |
| Q21 | CORRECT | (unanswerable) |
| Q22 | CORRECT | (unanswerable) |
| Q23 | CORRECT | (unanswerable) |
| Q24 | CORRECT | (unanswerable) |
| Q25 | CORRECT | (unanswerable) |

---

## 5. Failure Mode Deep Dives

### 5.1 GENERATION_OVERREACH — 12 cases (48%)

The retrieved context is correct, but the generated answer adds interpretation the notes do not contain.

Representative examples:

- **Q3** — Notes literally state the spreadsheet is used "more like a thinking space than a decision tool." Generated answer escalates to *"core issue with your financial tracking"* and *"dumping ground for ideas"* — definitive conclusions not in the source.
- **Q5** — Notes describe a father who "didn't react and changed the subject to weather in Breda." Generated answer reframes this as *"systemic patterns"* and *"doing the work"* — psychological inference, not a fact in the notes.
- **Q11 / Q13** — Generated answer uses second-person voice (*"You felt…"*, *"You thought you might have already sent it…"*) on what are first-person private journal entries. The notes do not contain this framing.
- **Q14** — A single instance of two deleted drafts is generalized to *"Your tendency toward delaying communication (avoidance)"* — a single data point converted to a behavioral pattern.

**Root-cause hypothesis:** The generation prompt is permitting (or actively inviting) interpretive synthesis on top of retrieved chunks. For a journaling product where users will trust the system to reflect their own words back to them, this is the most reputationally risky failure mode in the set.

### 5.2 INCORRECT_REFUSAL — 3 cases (12%)

The retrieved context contains the answer, but the model refuses anyway.

- **Q1** — Top-k retrieves chunk `N-7815`, which literally contains *"Wrote the first draft, sounded aggressively defensive, so I deleted it. Then I tried to make it sound chill, but it came out weirdly formal."* The model still answered: *"The provided context does not contain information about Maya or any drafts deleted on May 19."*
- **Q8** — Multi-hop question (`N-7811` + `N-7815`) where both notes were retrieved but the model refused.
- **Q16** — Phone-distraction physio note retrieved; model refused.

**Root-cause hypothesis:** The model is anchoring on the *absence of the literal name "Maya"* or *absence of an explicit date* in the chunk text — even though the chunks are first-person and the eval question scopes the subject. The refusal heuristic appears to be over-indexed on entity match.

### 5.3 GENERATION_HALLUCINATION — 3 cases (12%)

The generated answer states facts that are not in any retrieved chunk.

- **Q10** — Model claims *"the context does not specify if the failure occurred on May 17."* The retrieved context contains no dates at all, so this is a claim about the absence of a fact that was never in scope — invented framing.
- **Q19, Q20** — Model asserts *"Maya is not mentioned"* / *"Lina and Maya are not mentioned"* when both retrieved chunks discuss exactly those subjects.

These overlap with INCORRECT_REFUSAL in spirit but were classified as hallucination because the model made a *positive false claim about the retrieved context*, rather than just refusing.

### 5.4 FAILED_REFUSAL — 1 case (4%)

- **Q9** — A multi-hop question that *is* answerable from the notes. The model refused. (Judged as `FAILED_REFUSAL` because the refusal itself was an unsupported claim about the context.)

This is the inverse failure of §5.2 and shows the refusal threshold is unstable rather than uniformly biased.

---

## 6. Recommendations (prioritized by impact)

| Priority | Action | Targets failure mode |
|---|---|---|
| P0 | Tighten the generation prompt: require the answer to stick to the notes' literal wording; explicitly forbid second-person reframing and behavioral generalization from single instances. | GENERATION_OVERREACH (48%) |
| P0 | Add a "the notes say X, you may not extrapolate beyond X" instruction with 1-2 few-shot examples drawn from the failing Q3 / Q5 / Q14 cases. | GENERATION_OVERREACH |
| P1 | Rework the refusal heuristic. Current behavior conflates "the entity 'Maya' is not literally named in the chunk" with "the chunk is irrelevant." For a single-user journal, the speaker is the user — refusals should not depend on third-person entity matches. | INCORRECT_REFUSAL, GENERATION_HALLUCINATION |
| P1 | Add a retrieval-grounded refusal check: if top-k similarity exceeds threshold T, the model must answer or cite the chunk it considered insufficient. Currently it can silently refuse on high-similarity retrievals (Q1 retrieved the gold chunk at 0.708 and still refused). | INCORRECT_REFUSAL |
| P2 | Add a "do not claim absence of a date / name unless explicitly asked" rule to suppress the Q10-style hallucinations. | GENERATION_HALLUCINATION |
| P3 | Expand the eval to a second persona to confirm fixes don't overfit to Maya phrasing. | (validation) |

**Explicit non-recommendation:** Do not invest in retrieval tuning yet. Top-k is already pulling the gold notes in every failing case. Time spent on chunking / embedding model swaps would not move the needle.

---

## 7. Reproducing the Eval

From [Research/RAG/maya_eval/](../Research/RAG/maya_eval/) with Ollama running and the chat + embed models configured in `Backend/data/settings.json`:

```powershell
python generate_notes.py     # one-time; writes notes.json
python ingest.py             # resets isolated chroma/ and rebuilds the index
python run_eval.py           # writes results/raw.csv + raw.jsonl
python judge.py              # writes results/judged.csv
python report.py             # prints summary + writes results/summary.csv
```

Regenerate the corpus: `python generate_notes.py --force`.

### Artifacts

| Path | Contents |
|---|---|
| [Research/RAG/maya_eval/notes.json](../Research/RAG/maya_eval/notes.json) | Journal (~32 notes, stable note_ids) |
| [Research/RAG/maya_eval/questions.json](../Research/RAG/maya_eval/questions.json) | 25 questions with gold supporting notes |
| [Research/RAG/maya_eval/results/raw.csv](../Research/RAG/maya_eval/results/raw.csv) | Per-question: question, expected, generated, retrieved note IDs + scores + chunk text |
| [Research/RAG/maya_eval/results/raw.jsonl](../Research/RAG/maya_eval/results/raw.jsonl) | Same data, JSONL form |

### Isolation guarantee

The eval cannot touch production embeddings. [_bootstrap.py](../Research/RAG/maya_eval/_bootstrap.py) makes an mock of `app.services.chroma` to point at `maya_eval/chroma/` and a separate collection `maya_eval_chunks` *before* any production RAG module is imported.

---

## 8. Bring-Your-Own-Journals Sandbox (user_eval)

**Evaluation directory:** [Research/RAG/user_eval/](../Research/RAG/user_eval/)

Sibling sandbox to `maya_eval`, added so the RAG can also be spot-checked against real journals (my own) instead of only the synthetic Maya corpus. The synthetic corpus is good for regression tracking because the gold notes are fixed, but its phrasing is artificial. Running the same pipeline over journals I wrote myself is a low-friction qualitative check on whether the failure modes from sections 3 to 5 (especially GENERATION_OVERREACH and INCORRECT_REFUSAL) also appear on real personal data, and it gives a way to validate the section 6 fixes against journals that were not in the synthetic training distribution.

### 8.1 Scope

* Same isolation pattern as maya_eval (its own Chroma path, its own collection `user_eval_chunks`), so user data never lands in production embeddings and never collides with the Maya eval.
* Supports a mix of audio (`.wav`, `.mp3`, `.m4a`, `.webm`, `.ogg`) and text (`.txt`, `.md`). Audio is transcribed via the same WhisperX pipeline the production app uses.
* Light flow only: ingest plus an interactive ask loop. No gold answers, no LLM-as-judge, no failure mode taxonomy. Manual inspection is sufficient because I already know what the correct answer should be.

### 8.2 Files

| File | Purpose |
|---|---|
| [_bootstrap.py](../Research/RAG/user_eval/_bootstrap.py) | Isolates Chroma to `user_eval/chroma/` and collection `user_eval_chunks` before any RAG import. |
| [ingest.py](../Research/RAG/user_eval/ingest.py) | Walks `journals/`, transcribes audio, reads text/markdown, chunks via the production chunker, indexes into the isolated collection. Wipes and rebuilds on each run for reproducibility. |
| [ask.py](../Research/RAG/user_eval/ask.py) | Interactive REPL. Type a question, see the generated answer plus the filename, score, and chunk excerpt for each retrieved source. |
| `journals/` | Drop journal files here. Gitignored so private journals never get committed. |

### 8.3 Reproducing

From [Research/RAG/user_eval/](../Research/RAG/user_eval/) with Ollama running:

```powershell
# 1. Drop your journal files into journals/
# 2. Chunk and index into the isolated collection.
python ingest.py

# 3. Ask questions. Type :q to exit. Optional --top-k flag.
python ask.py
```

Re-run `ingest.py` whenever the `journals/` folder changes; it resets the collection so there are no stale or duplicate chunks.

---

## 9. Next Steps

1. Implement P0 prompt changes against the same eval set and re-run — expected effect: large drop in GENERATION_OVERREACH share.
2. Implement P1 refusal logic — expected effect: INCORRECT_REFUSAL → 0, FAILED_REFUSAL stable or down.
3. Once the eval flips from "diagnostic" to "regression gate," wire `report.py` summary into CI so prompt / model changes have a measurable failure-mode delta.
