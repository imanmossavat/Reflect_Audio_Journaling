# Evaluating & Improving the Reflect Journaling AI

### A plain-language report on how the "ask your journal a question" feature was tested and made better

**Author:** Mathijs van den Heiligenberg
**Date:** June 2026

---

## 1. What this feature does (in one paragraph)

Reflect lets you record audio journal entries. The feature evaluated here lets you **ask
questions about your own journals in plain language** — for example *"Where do I work now?"* or
*"What patterns show up in how I handle stress?"* — and get an answer drawn from what you actually
wrote. Under the hood this is a two-step system: first it **finds** the handful of journal entries
most relevant to your question, then it **writes** an answer based only on those entries. The
industry name for this design is **RAG** (Retrieval-Augmented Generation): *retrieve* the right
notes, then *generate* the answer from them.

The whole point of the work in this report was to make sure that (a) it finds the *right* notes
and (b) it answers *truthfully* — without making things up or refusing to answer when the answer
is right there.

---

## 2. Why evaluation was needed at all

An AI that answers questions can fail in ways that are invisible unless you measure them. It can:

- pull up the **wrong journal entries**, then answer confidently from the wrong material;
- **invent facts** that aren't in your journals ("hallucinate");
- **refuse to answer** ("I don't know") even when the answer is sitting right in front of it;
- get **time confused** — e.g. report your *old* job when you asked about your *current* one,
  just because the old note was longer or more detailed.

You cannot fix what you cannot measure. So before improving anything, I built a **repeatable test
bench** that could put a number on each of these failure types. Every improvement after that was
judged against the test bench.

---

## 3. Two complementary ways to test

There is no single way to grade an AI assistant, because it does two quite different jobs:

1. **Answering factual questions** about your journal ("Where do I work now?") — these have a
   *right answer*, so they can be graded objectively against a known answer key.
2. **Open-ended reflective work** ("What patterns appear in how I handle stress?", or generating a
   thoughtful follow-up question) — there is *no single right answer*, so quality has to be judged.

I built a separate testing method for each:

| Method | Used for | How it grades | Section |
|---|---|---|---|
| **A. Known-answer exam** | Factual questions | Mechanically, against answers I wrote myself | §4–5 |
| **B. AI-judge scoring (RAGAS-style)** | Open-ended quality + comparing AI models | A second AI scores each answer 1–5 on quality | §6 |

The two are not rivals — they cover different risks. The exam proves the assistant gets *facts*
right; the AI-judge scoring proves its open-ended answers are *grounded and useful*, and helped
pick which underlying AI model to use in the first place.

---

## 4. Method A — The known-answer exam

Think of it as giving the AI an **exam where I already know all the correct answers**.

To do that I wrote two sets of **fictional journals** for two fictional people, plus a list of
questions with a known correct answer for each. Because I wrote the journals, I know exactly which
entry contains each answer — so I can check, automatically and objectively, whether the AI found
the right entry and gave the right answer.

| Test set | Persona | Difficulty | What it stresses |
|---|---|---|---|
| **Baseline** | "Maya" — 22 entries | Easier | Can it find the single right note and answer faithfully? |
| **Stateful** | "Niels" — 34 entries | Harder | Can it handle **things that change over time** — past vs. current vs. planned job, questions needing several entries combined? |

The second set is the demanding one. Real journals describe a life that *changes* — you switch
jobs, end and start relationships, abandon and restart projects. A good assistant must know that
the *newest* note isn't automatically the *current* truth, and must sometimes combine several
entries to answer one question. The "Niels" set was purpose-built to catch exactly those mistakes.

Each answer is automatically sorted into a clear category — **Correct**, **Refused when it
shouldn't have**, **Partially correct**, **Wrong state** (right topic, wrong point in time), and so
on — so progress is visible at a glance rather than buried in opinion.

> **Why this is trustworthy:** the scoring for *finding the right notes* is purely mechanical —
> the note is either in the shortlist or it isn't, no judgment call. Every test run is also stamped
> with the exact version of the code that produced it, so any result can be reproduced later. In
> short: **the exam is graded the same way every time.**

---

## 5. What was changed, and what each change revealed

The work ran in three phases. Crucially, the test bench was built *in the middle* — so the later
improvements could be proven, not just assumed.

### Phase 1 — Help it find the right notes (smarter filtering)

The original system guessed which notes were relevant using crude keyword matching (e.g. it only
recognised "anxious" if you literally typed the word "anxious"). I replaced this with proper
**filters on real facts** — when an entry was written, and whether it was a voice or text entry —
so the system can narrow down to the right time window and entry type *before* it even starts
ranking. This is the difference between a keyword guess and a structured search.

### Phase 2 — Build the exam (the test bench)

This is the measurement system described in Section 3. Nothing about the AI improved here, but
from this point on **every claim of improvement could be backed by a number.** This is the
single most important professional discipline in the whole project: change one thing, re-run the
exam, keep the change only if the score genuinely improved.

### Phase 3 — Rank the found notes more intelligently (the "reranker")

I added a second, smarter model whose only job is to **re-order** the shortlist of candidate notes
so the most relevant ones rise to the top. (Technically: a "cross-encoder reranker" — it reads the
question and each note *together* and scores how well they match, rather than matching keywords.)

**An honest finding here:** the reranker only helped on questions that needed **several notes**
combined. On easy one-note questions it made no difference, because the system was already putting
the single right note at the top — there was simply no room to improve. This is a genuine, useful
result: *a tool only proves its worth where the problem is actually hard.* Since real journaling
questions tend to be the multi-note kind, the reranker stays switched on.

### The breakthrough: the real bottleneck wasn't *finding*, it was *answering*

This is the most important finding in the report, and a slightly surprising one.

After Phases 1 and 3, the hard "Niels" exam was still only scoring **47% correct**. I expected the
problem to be retrieval — that the AI couldn't *find* the right entries. The test bench proved the
opposite: in nearly every failure, **the right entry had been found and handed to the AI, and it
still refused to answer**, saying "I don't know" when the answer was right there in front of it.

The cause turned out to be a single overly-cautious instruction in how the AI was prompted — it
was being told, in effect, "if in any doubt, say you don't know," and it took that far too
literally. I rewrote that one instruction.

**The result of that single change:**

| | Before the prompt fix | After the prompt fix |
|---|---|---|
| **Correct answers** (Niels exam) | 47% (7 of 15) | **67% (10 of 15)** |
| Refused when it shouldn't have | 5 | **1** |

A **+20 percentage-point jump in accuracy** from rewriting one instruction. Because the test bench
confirmed the *note-finding* numbers were **byte-for-byte identical** before and after, we know for
certain the entire improvement came from the AI now being *willing to answer* — nothing else
changed. Without the test bench, this would have been guesswork; with it, it's proven.

---

## 6. Method B — Judging open-ended quality with AI judges (RAGAS)

The exam in §4–5 works because factual questions have known answers. But the assistant's most
valuable work is *open-ended* — reflecting on themes, or generating a thoughtful follow-up question
— and there's no answer key for "what's a good reflective question." For that I used the industry-
standard **RAGAS** approach: have a **second AI act as an impartial judge**, scoring each answer
from 1 to 5 on specific quality dimensions.

To keep this honest, I used **two different judge models** rather than one, and recorded how much
they agreed — so a single biased judge can't skew the result. I also combined the AI judges with
**simple mechanical rule-checks** wherever a rule was black-and-white (e.g. "the follow-up question
must be under 20 words and must not be a yes/no question"), so those facts weren't left to opinion.

I ran three studies this way:

**6.1 — Answer quality on reflective questions.** Seven open-ended questions (e.g. *"What
recurring patterns appear in how I handle work stress?"*), each answer judged on:

- **Faithfulness** — does every claim actually come from the journal, with nothing invented?
- **Relevancy** — does it answer the question, without vague filler?
- **Grounding/precision** — does it use the specific evidence, not generic statements?

**6.2 & 6.3 — Follow-up-question quality.** Whether the assistant's generated reflective
questions are **specific** (reference real themes from the journal), **deep** (likely to prompt
genuine reflection), and **grounded** (anchored in what was actually written) — plus the mechanical
rule-checks above.

### What this revealed: the choice of AI model matters enormously

The single clearest result was how differently the candidate AI models performed. On answer
quality (scored 1–5 by the judges):

| AI model | Faithfulness | Relevancy | Grounding | Verdict |
|---|---|---|---|---|
| **Llama 3** | 4.0 | 4.0 | 3.5 | Strong — grounded, on-topic |
| Mistral | 1.6 | 1.6 | 1.4 | Weak — vague and poorly grounded |

That's a night-and-day difference, and it's exactly the kind of thing that's invisible without
measurement. On the follow-up-question task there was a second useful trade-off: one model
(**gpt-oss:20b**) followed the formatting rules perfectly (100% rule-compliance), while **Llama 3**
wrote slightly more insightful questions but broke the length/format rules more often. Knowing this
lets me choose the right model for each job rather than guessing.

**The takeaway:** the AI-judge method doesn't just produce a grade — it turns "which model should we
use?" and "are the open-ended answers actually trustworthy?" into measured decisions instead of
hunches.

---

## 7. Where things stand today

- A **repeatable, objective evaluation system** now exists. Any future change to the assistant can
  be measured against it before shipping — no more guessing.
- The assistant now **finds the right journal entries reliably** (it located relevant material for
  every answerable question on the hard test set).
- The biggest real-world quality problem — the assistant **needlessly refusing to answer** — was
  diagnosed and largely fixed, lifting accuracy on the hard test set from **47% to 67%**.
- A **second, AI-judge–based evaluation** (RAGAS) confirms the open-ended answers are grounded and
  on-topic, and turned the **choice of underlying AI model** into a measured decision — the gap
  between candidate models was large (e.g. 4.0 vs. 1.6 out of 5 on answer quality).
- Each experiment is **logged and reproducible**, so the reasoning behind every decision is on the
  record (see the engineering log, `FINDINGS.md`).

## 8. What's next

- Some questions need **more than five entries** combined to answer fully; the system currently
  looks at five, which caps the score on those. Raising that limit is a straightforward next step.
- Continue tuning the note-ranking now that the assistant actually commits to answers (previously
  the over-refusal masked any ranking improvement).
- Explore a stronger note-matching model for the hardest "how has this changed over time"
  questions, where the current one struggles to separate good notes from mediocre ones.

