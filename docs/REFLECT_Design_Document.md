# REFLECT Project — Design Document (Document A, v3)

*This markdown file is currently the most up to date copy — it has edits the
matching PDF does not have yet. Regenerate the PDF from this file next time
a polished copy is needed; until then, this file is canonical, not the PDF.*

**Governs intent and design rationale.** The companion Implementation
Contract (Document B) governs schema and mechanism. Where the two appear to
disagree, this document wins and the contract is treated as a bug to fix.
This revision folds in everything worked out after the first draft: the
existing Gibbs flow as it actually runs today, mid-conversation source
consultation, provenance labeling, a tracked list of research questions, and
— this round — two sharpened constraints, one new open question, and a
small set of supporting (not core) references.

---

## 1. Purpose and scope

You are designing a small interactive process that helps a student better
understand what happened, why it happened, and what to do next. The focus is
on helping someone make sense of a messy or confusing experience — not on
producing a polished write-up of it.

This document supersedes the earlier baseline architecture and developer
guides. Those documents were one possible implementation of the founding
brief below, not the goal itself, and in places their architecture grew more
elaborate than the interaction actually needed. This revision is a return to
the founding brief, not a departure from it — the original brief never
mandated a fixed stage sequence; it posed "Socratic questioning, Gibbs, …" as
one open question among several under Direction C below.

### The existing Gibbs flow, and how this design relates to it

The running product today already implements a Gibbs cycle: the student
picks which sources are in scope, states an intent, and then moves through
phases (description, feelings, and so on) driven by AI-generated questions.
On every turn within a phase, the student currently has three moves
available: answer and get another question, answer and advance to the next
phase, or consult their sources instead of answering. This design does not
remove that shell. It changes what sits underneath it: Gibbs-style phase
names can stay as labels the student sees, but they stop being gates the
system enforces — nothing about the phase blocks progress or forces a rigid
order. What must not survive is the phase acting as code-level gatekeeping
(keyword-matched completion checks, forced sequencing). What may survive,
deliberately, is the phase as a soft, human-facing label — useful for
orientation, meaningless to the underlying mechanism.

The third per-turn move — consulting sources mid-conversation — is not a
detour outside the reflection. It is a normal part of it: someone gets stuck
on a question, goes back to what they actually wrote, and comes back
informed. Whatever is learned from that detour feeds back into the same
continuity mechanism as anything else said in the conversation — it is not a
separate, disconnected side-channel.

### Which founding directions this build draws on

The founding brief offered four parallel design directions to choose from.
This build draws mainly on **Direction C — Reasoning & Interpretation**
(adaptive questioning, exploring alternatives, avoiding premature
conclusions). **Direction A — Memory & Capture** (the Notebook-LM-style
retrieval the brief itself names as an example) is more central than
originally scoped: source consultation is a routine, per-turn mechanic, not
an occasional side path. **Direction B — Structure & Visualization**
(timelines, visual maps) stays out of scope for this build — a tag graph
view already exists as a separate, pre-existing feature and is not something
this design produces. **Direction D — Entities & Relationships** is
partially revisited: hierarchical tags and provenance-labeled entities are
now a named future direction (§10), though not part of the current build.
This is an updated scope decision, not an oversight.

## 2. Current situation and context

Students commonly remember situations only partially, describe events
without really understanding them, jump quickly to conclusions, and struggle
to turn insight into action. As a result, reflection can become writing
about experience without actually improving understanding. Thinking is often
invisible, unstructured, and difficult to revisit over time. This project
explores how interaction design can support that process.

## 3. Core idea

The tool helps someone reconstruct experience, organize thoughts, explore
explanations, notice patterns, and make decisions. The goal is helping
people understand their own experience more clearly — the system supports
that understanding, it does not perform it on the student's behalf.

## 4. Theory background

Three complementary perspectives from cognitive science and learning theory
explain why reflection is difficult and how interaction design can support
it. They are used here as design lenses, not as a psychological model of
reflection: they help us judge whether an interface, a piece of structure,
or a turn of conversation supports reflective thinking or interrupts it.

### Reflection as inquiry — Dewey

Dewey, J. (1910), *How We Think*. Reflection is not passive thinking but an
active process of inquiry grounded in experience. It begins when a person
encounters something uncertain, incomplete, or confusing, and proceeds
through questioning, interpreting, and revisiting. Reflection is tied to
action: the goal is not describing what happened but reorganizing experience
into something that can guide future decisions. Students often describe
situations without examining why they happened or how they connect to
broader patterns — the design challenge is supporting inquiry rather than
documentation.

Modern interpretation: Rodgers, C. (2002). "Defining reflection: Another
look at John Dewey and reflective thinking." *Teachers College Record*,
104(4), 842–866.

### Dual-process theory and cognitive friction

Dual-process theories distinguish fast, intuitive thinking (System 1) from
slower, deliberate reasoning (System 2). Everyday interpretation often
relies on System 1, producing quick but oversimplified explanations. System
2 is more likely to engage when something feels uncertain, conflicting, or
effortful. Cognitive friction — ambiguity, contradiction, alternative
explanations — can trigger deeper reflection by encouraging reconsideration
rather than immediate acceptance. Too much friction, though, becomes
counterproductive if the interaction grows exhausting or overly complicated.

Sources: Kahneman, D. (2011) *Thinking, Fast and Slow*. Stanovich, K. E., &
West, R. F. (2000), *Behavioral and Brain Sciences*, 23(5), 645–665. Evans,
J. St. B. T., & Stanovich, K. E. (2013), *Perspectives on Psychological
Science*, 8(3), 223–241.

### Cognitive Load Theory and external support

Working memory is limited; learning and reasoning suffer when effort is
spent on irrelevant or poorly structured information. CLT distinguishes
intrinsic load (the task's own complexity), extraneous load (unnecessary
effort from poor design), and germane load (productive effort that builds
understanding). Reflection tools should reduce unnecessary mental effort by
offloading memory and externalizing structure — without removing the
productive difficulty reflection actually requires.

Germane-load-increasing question patterns worth reusing directly: ask why,
not only what; move from concrete to abstract; compare and contrast against
a similar past situation; analyze what assumption turned out wrong; predict
before, compare after.

Sources: Sweller, J. (1988), *Cognitive Science*, 12(2), 257–285. Sweller,
J., van Merriënboer, J. J. G., & Paas, F. (2019), *Educational Psychology
Review*, 31, 261–292.

### Implications for design

Together these perspectives mean a reflective system must balance three
goals: supporting open-ended inquiry (Dewey), encouraging deeper reasoning
at the right moments (dual-process), and reducing unnecessary cognitive
burden (CLT). The challenge is not simply "help users reflect" but to
balance ease of use with moments of productive difficulty.

## 5. Design principle: grounded in sources, not interrogating the conversation

An earlier iteration of this design extracted "facts" from what the student
said in chat and used that running list to keep probing — "you mentioned
feeling ignored, can you say more about that." That is organized around
checking off the student's own statements back at them. It reads as
interrogation because it is structurally interrogation, however politely
phrased.

The fix is not to extract facts more carefully. It is to stop generating
questions from a ledger of the conversation and instead generate them from
the **source material itself** — the journal entries the student actually
wrote — plus a light, regenerated sense of where the conversation currently
stands. The system's job is closer to discussing a piece of writing with
someone than auditing what they have told it so far.

### A second, related problem: open questions are genuinely hard to answer

Grounding solves whether a question is honest. It does not automatically
solve whether a question is easy to answer. A fully open question — even a
well-grounded one — asks the student to generate an answer from nothing,
which is real cognitive work on top of the reflective work itself. Two
lighter-weight forms are preferred where they fit naturally: a short
question paired with a verbatim quote of something the student actually
wrote, or a small set of answer options to react to instead of composing
free text. Reacting is consistently easier than generating from a blank
state.

This must not become a way of putting words in the student's mouth through
the back door. Answer options are a menu to react to, not a guess at the
student's internal state presented as fact — every set of options needs an
easy "something else" escape, and none may assert a feeling or motive on the
student's behalf. This is the same constraint as §7's "words in the
student's mouth," applied to a new surface.

## 6. The core objects

A small number of objects are sufficient for the loop. Nothing else
persists — no fact ledger, no stage label as a gate, no transcript replay,
no turn counters, no versioned state files.

| Object | What it is | Who writes it |
|---|---|---|
| Source | A journal entry the student selected, addressed at the level of the individual claims or statements within it. Given by the student; what gets derived from it is labeled per §6.1 below. | Given by the student |
| Focus | What the student says they want right now (explore why, decide what to do, just talk). A lens, not a gate, and slow-changing — set once, rarely revised. | Set by the student; the AI may suggest a change, never applies one itself |
| Gist | One paragraph, rewritten each turn: where the conversation currently stands. Replaces transcript replay. Updated the same way whether the turn was a normal answer or a mid-conversation source consultation. | Written by the extraction call, grounded in cited Source units |
| Open Thread | The one thing being explored right now. Singular, not an accumulating list. Replaced, not appended to, when settled. | Written by the extraction call |

Focus and the per-turn choice to consult sources are deliberately not the
same mechanism. Focus is a slow, session-level lens the student sets rarely.
Consulting sources is a fast, every-turn option — available whenever a
student is stuck, independent of Focus. Collapsing the two would mean the
system loses the distinction between "what I'm generally trying to do" and
"I need to go check something right now," which are different kinds of
decisions and change at different speeds.

### 6.1 Provenance: every piece of information is labeled

This resolves a question the design carried for a while: should a citation
point at a raw chunk of text, or at a claim extracted and verified by the
student? The answer is that both are the same mechanism wearing a different
label, not two competing designs. Every unit of information in the system —
a Source unit, a tag, a claim surfaced during reflection — carries one of
three provenance labels:

- **Direct** — the student's own words, unmodified.
- **AI-derived, validated** — the system proposed something (a paraphrase,
  a claim, a tag) and the student confirmed it.
- **AI-derived, unvalidated** — the system proposed it, nobody has confirmed
  it yet.

This label is a schema-level property of the information itself, not a
presentation detail bolted on for the reflection flow — it must hold true
regardless of how Gibbs or the RAG search happen to work underneath.
Anything produced from unvalidated material must carry that fact forward
visibly, not silently launder it into something that looks confirmed.

### 6.2 Verified / unverified at ingestion

When a document is submitted, it starts **unverified**. Unverified material
is excluded from both the reflection flow and RAG search by default — not
deleted, not hidden, just not in scope until the student reviews it. The
student can see unverified material, review and verify it, or choose to use
it anyway. Choosing to use unverified material is allowed, but anything the
flow produces from it must be visibly marked "unverified / AI-generated"
downstream, per §6.1.

A reflection session can itself become a new, cleaner source once it
concludes — this reuses an existing capability rather than adding one, and
gives messy, large journal entries a path toward becoming more addressable
material over time. This needs to be weighed against source bloat: not
every reflection is worth keeping as a standalone source, and this tradeoff
is tracked as a research question in §12.

### Mapping theory to mechanism

| Theory | Implication for design | Where it shows up in this build |
|---|---|---|
| Dewey — evolving inquiry | Avoid fixed interpretation; support revisiting and reconsideration. | Open Thread is singular and replaceable, never an accumulating checklist; the AI never "closes" a topic, the student does. |
| Dual-process — avoid premature conclusions | Trigger System 2 through productive friction; resist quick synthesis. | Every substantive claim the AI makes must cite a Source unit; provenance labels make the strength of that grounding visible rather than assumed. |
| CLT — externalize memory, reduce extraneous load | Reduce extraneous load; don't make the student or the model re-derive context every turn. | Gist replaces transcript replay; quote-anchored and multiple-choice question forms reduce the effort of answering, not just the effort of remembering. |

## 7. Failure modes this design guards against

**Interrogation / repetition.** Solved structurally by §5 — grounding in
sources rather than a fact ledger, plus a single live Open Thread instead of
an accumulating list of things to check off.

**Questions that are honest but too hard to answer.** Preferring
quote-anchored or multiple-choice forms over fully open questions where they
fit, per §5 — while keeping an escape hatch so options never assert a
feeling on the student's behalf.

**Gist drift.** A rolling summary written from the previous summary, turn
after turn, compounds distortion the way a long game of telephone does.
Mitigated by requiring every claim in Gist to be traceable to a cited Source
unit, so it stays auditable rather than silently drifting from what was
actually said.

**Words in the student's mouth.** The system must never assert a feeling,
motive, or interpretation the student did not state — their reflection
belongs to them. This holds even when the guess is phrased tentatively or
hedged ("it sounds like maybe...") rather than stated as fact — reaching
past what the student actually wrote erodes trust whether or not the guess
turns out to be right. This is a hard constraint on the conversational
response, on what gets written into Gist, and on how answer options are
phrased — not a stage-specific check.

**Drift after a dismissal or tangent.** Handled the way it always should
have been: acknowledge briefly, then return to the live Open Thread with one
question — never push past resistance, never repeat a question that has
already been asked and answered, even briefly.

**Premature closure.** The AI does not get to decide a line of inquiry is
resolved on its own intuition; resolution of the Open Thread and any shift
in Focus both route through something the student can see and confirm, not
something the model infers silently.

**Friction that doesn't lead anywhere.** §4's cognitive-friction mechanism
is only productive if a moment of friction points toward a next question.
Surfacing a discrepancy or contradiction with no interpretive next step
reads as a random surprise, not a prompt to think — it can disconnect the
question from what the student actually cares about instead of deepening
it. Every friction-inducing moment this system generates needs an implicit
"and here's where we could take that," not just an open contradiction left
sitting there.

**Unverified material silently treated as fact.** Provenance labels (§6.1)
exist specifically so an unconfirmed AI claim can never be presented with
the same confidence as something the student actually wrote or actually
confirmed.

## 8. AI as support

In this project, AI is not the thinker. It is a support layer: cleaning
messy notes, helping organize information, asking clarification questions,
retrieving earlier notes or memories. The design challenge throughout is how
to support human thinking without replacing it.

## 9. What good work looks like

- Focuses on one clear interaction rather than many half-built ones.
- Helps the student understand something new about their own experience.
- Makes thinking more visible without adding interface overhead.
- Reduces confusion or overload rather than adding to it.
- Leads toward meaningful action.
- Is tested against real or realistic sessions, not just designed on paper.

## 10. Open and deferred decisions

These are scope decisions, not implementation details, which is why they
belong here rather than only in the contract. Until resolved, the
Implementation Contract treats all of them as out of scope for the current
build.

**OPEN / DEFERRED — Advisor-facing view.** An advisor (someone other than
the student) being able to see and correct session state is described in
earlier materials as a real safeguard. Provenance labels (§6.1) are a
natural mechanism for this — an advisor would dispute a label rather than
hand-editing prose — but whether advisor correction is in scope at all is
still undecided.

**OPEN / DEFERRED — Closing artifact.** The founding brief's core idea
includes helping the student end up with something reusable — a timeline,
themes, stakeholders, lessons, actions — not just a chat log. Whether this
build produces a generated closing document is undecided. The current
contract covers only the per-turn conversational loop.

**OPEN / DEFERRED — Hierarchical tags.** Tags should be able to nest (e.g. a
learning outcome sits under a course, which sits under a broader education
category), rather than the flat tag list that exists today. This is
recorded as a real design principle so nothing built now forecloses it, but
building the nested structure itself is separate, later work.

**OPEN / DEFERRED — Per-document inclusion rules.** Independent of
provenance and verification status, a student should be able to mark a
specific document as never included in RAG or reflection, always included,
or included by default rules. This is a separate control from verification
— a fully verified document could still be marked never-include. Recorded
as a principle; the actual controls are later work.

## 11. Critical design questions — a standing self-check

Re-run this against whatever gets built, not just once at the start:

- Dewey — am I killing inquiry by structuring too early?
- Dual-process theory — am I failing to trigger deeper reasoning?
- Cognitive Load Theory — am I overloading working memory with unnecessary
  UI complexity or interaction steps?

## 12. Research questions to track after building

Where §11 asks what might be going wrong in principle, this section asks
how we'd actually find out in practice, once a working version exists.
Grouped by what each question is actually testing.

### A. Does the core idea even work?

- Does grounding in sources and citations actually remove the interrogation
  feeling, compared to the old system? This is the central hypothesis of
  the redesign — needs real conversations, not a read-through.
- Does the Gist stay accurate over a long conversation, or does it quietly
  drift even with the citation rule? Check it against the real sources
  after 10–15 turns.
- Does a single live Open Thread feel focused, or does it feel too narrow —
  like the system won't let the student hold more than one thing in mind
  at once?
- Does letting students redirect Focus themselves actually get used, or is
  the suggestion ignored while drift continues anyway?
- People want a low-effort mode some days and more depth on others. Does
  Focus need its own depth/effort setting to capture that, or is preferring
  quote-anchored and multiple-choice questions (§5) already enough to cover
  a low-effort day? Not yet known — a real research question, not a design
  decision to make from a desk.

### B. Is the theory actually happening, not just cited?

- Dewey — are we structuring things too early and quietly killing open
  exploration?
- Dual-process — does grounding actually push people toward deeper
  engagement, or do they just click through citations without reading
  them?
- CLT — does this genuinely feel lighter than the old system, or did the
  mental effort just move somewhere else — for instance, onto reviewing
  claims?

### C. Does claim extraction and verification work in practice?

- How many claims does a typical entry produce, and does reviewing them
  feel like reflection or like homework? Too many claims risks
  reinventing the tedious fact-checklist this design was meant to remove.
- What happens to a claim nobody ever reviews — does it just sit unused
  indefinitely?
- What happens to a rejected claim — remembered as rejected, or forgotten
  entirely?
- Does hiding unverified material by default cause people to simply never
  verify, leaving their journal effectively unused? A real adoption risk,
  not just a design nicety.
- Does extraction correctly resolve who "he/she/they" refers to across
  topic switches, and correctly capture someone's final landed position
  rather than an earlier one they talked themselves out of? Directly
  testable against real messy recordings.

### D. Which question format actually works, and when?

- Open question vs. quote-anchored question vs. multiple-choice — which
  performs better, and in what situations? Does a quote of the student's
  own words genuinely make a question easier to answer? Does
  multiple-choice ever start to feel like the system is guessing at the
  student's feelings for them?

### E. What we deliberately don't know yet

- How do different people actually journal — short vs. long, emotional vs.
  analytical, clean vs. messy? Not something this build solves; the thing
  that would tell us whether one system design can genuinely serve
  everyone.
- Source bloat vs. value — as reflections turn into new sources over time,
  at what point does a student's source list become clutter rather than
  useful material?

### F. Questions the two parked decisions would resolve

- Advisor view — is disputing a provenance label enough correction power,
  or do advisors need to edit text directly?
- Closing artifact — does a final built output (timeline, themes, actions)
  add real value, or is the conversation itself sufficient on its own?

## 13. Related work — supporting references, not core theory

§4 is the core theory this design is built on and stays as written above.
The references below were found while checking this design against the
wider HCI reflection literature. They are supporting context, not
foundational — nothing in §4–§9 depends on them, and they are recorded here
so the connection isn't lost, not to expand the theory section.

- **Baumer, E. P. S. (2015). "Reflective Informatics: Conceptual Dimensions
  for Designing Technologies of Reflection." CHI 2015, 585–594.** Proposes
  three dimensions of reflection — Breakdown, Inquiry, Transformation —
  that map closely onto this design's own mechanism: cognitive friction
  (§4) resembles Breakdown, source-grounded retrieval and the live Open
  Thread resemble Inquiry, and an Open Thread being replaced rather than
  appended to resembles Transformation. Worth citing directly if this
  design is written up formally — the overlap is close enough that a
  reviewer would notice it either way.

- **Tarvirdians, M., Chandrasegaran, S., Hung, H., Jonker, C. M., & Oertel,
  C. (2026). "Reflecti-Mate: A Conversational Agent for Adaptive
  Decision-Making Support Through System 1 and System 2 Thinking." UMAP
  2026.** A between-subjects study (N=128) found an agent that adapted to
  the individual's thinking pattern produced more personalized, integrative
  reflective language than a fixed-question baseline agent. Not about
  journaling specifically — it's decision support — but it's the closest
  existing empirical precedent for choosing adaptive questioning over a
  fixed sequence (§1's Direction C choice), and its study design is a
  reasonable template for testing our own research question A.1.

- **Pammer-Schindler, V., & Prilla, M. (2021). "The Reflection Object: An
  Activity-Theory Informed Concept for Designing for Reflection."
  Interacting with Computers, 33(3), 295–310.** Proposes a "reflection
  object" — a single concept describing both what is being reflected on
  and what changes through reflecting on it. This is a different, more
  abstract level of framing than the four concrete objects in §6; on an
  initial look it does not appear to overlap structurally, but the full
  paper is worth reading before making any claim that the four-object
  model here is novel.

A few additional leads turned up but haven't been read or verified yet —
recorded so they aren't lost, not treated as confirmed: a system called
KRIYA (participant quotes on friction and trust suggest direct relevance to
§5 and §7, but the source paper itself hasn't been confirmed); "DiaryMate"
(CHI 2024, human-AI collaboration in personal journaling specifically); "
Introspectus AI" (2025, long-term dialogue-based reflection, possibly
relevant to how Gist should behave across sessions rather than within one);
and Li, Dey, & Forlizzi's 2010 stage-based model of personal informatics
systems, a standard older foil for the no-fixed-stages decision in §1.

## 14. Relationship to the Implementation Contract (Document B)

This document governs intent: the core objects, the theory grounding, and
the failure modes guarded against. The companion Implementation Contract
governs mechanism: schema, prompt assembly, the turn loop, and failure
handling. Document B should never need to restate why a decision was made —
it points back here. If the contract's behavior ever contradicts a
principle stated in this document, that is a bug in the contract to fix,
not a tiebreak to negotiate turn by turn.
