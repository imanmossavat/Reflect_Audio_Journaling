# Table of Contents

[Current situation and context](#_Toc229403098)

[Core idea](#_Toc229403099)

[Design directions](#_Toc229403100)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; [A. Memory & Capture](#_Toc229403101)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; [B. Structure & Visualization](#_Toc229403102)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; [C. Reasoning & Interpretation](#_Toc229403103)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; [D. Entities & Relationships](#_Toc229403104)

[AI as support](#_Toc229403105)

[Example interaction ideas](#_Toc229403106)

[What good work looks like](#_Toc229403107)

[Theory background](#_Toc229403108)

[Reflection as inquiry](#_Toc229403109)

[Dual-process theory and cognitive friction](#_Toc229403110)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; [Sources](#_Toc229403111)

[Cognitive Load Theory and external support](#_Toc229403112)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; [Sources](#_Toc229403113)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; [Implications for design](#_Toc229403114)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; [Critical reflection questions](#_Toc229403115)

# REFLECT Project - Student Guide

1\. What is this project?

You will design a small interactive process that helps a student better understand:

- what happened
- why it happened
- what to do next

The focus is on helping someone make sense of a messy or confusing experience.

## Current situation and context

From my perspective as someone working with students, I often notice that students:

- remember situations only partially
- describe events without really understanding them
- jump quickly to conclusions
- struggle to turn insight into action

As a result, reflection can become writing about experience without actually improving understanding.

The problem is that thinking is often _invisible_, _unstructured_, and _difficult to revisit_ _over time_.

This project explores how interaction design could help support that process.

## Core idea

You are designing a tool that helps someone:

- reconstruct experience
- organize thoughts
- explore explanations
- notice patterns
- make decisions

The goal is helping people understand their own experience more clearly.

## Design directions

Below are different ways of approaching the problem. You do **not** need to combine everything. Choose one direction that interests you and explore it deeply.

### A. Memory & Capture

Sometimes the problem starts before reflection even happens.

People forget details, lose context, or only remember fragments.

This direction explores:

- capturing moments while they are fresh (audio?, text, trackers,…)
- organizing messy thoughts (tags, color-schemes, mind-maps,…)
- helping users reconstruct situations later (Notebook LM styel retirieval and question answering - Retrieval augmented generation)

Possible questions:

- How can someone quickly capture a moment?
- What information becomes important later?
- How can fragmented memories become usable?
- Is the user talking about a structural point (trait) or just transient events?
- What is the magnitude, severity, or size of the issue? What is the saliency of the point being discussed?

### B. Structure & Visualization

Many reflections stay as long blocks of text.

But text alone can make it difficult to see relationships, sequences, or causes.

This direction explores:

- timelines
- visual maps
- spatial organization
- connections between events

Possible questions:

- How can structure become visible?
- How can users see what led to what?
- How can experiences become easier to overview?

### C. Reasoning & Interpretation

Students often stop at their first explanation.

This direction explores tools that support deeper thinking and _exploration_.

Examples:

- comparing explanations
- checking assumptions
- exploring alternatives
- organizing evidence

Possible questions:

- How can a system encourage better reasoning?
- How can users test their own interpretation?
- How can uncertainty become visible?
- Would pre-defined questions work, or do we need adaptation (AI asking questions)?
- Which system is best? Socratic questioning, Gibbs, …

### D. Entities & Relationships

Experiences often involve recurring things:

- people
- projects
- meetings
- feedback
- tools
- themes

This direction explores ways to make these visible across time. Possible questions:

- What keeps appearing in someone's experience?
- How are situations connected?
- Can users explore relationships between people, events, or themes?
- How should we handle AI transcription errors (what interface is needed for entity alignment)

## AI as support

In this project, AI is not the "thinker."

Instead, AI can act as a support layer.

For example:

- cleaning messy notes
- helping organize information
- asking clarification questions
- retrieving earlier notes or memories

The important design challenge is:

How do we support human thinking without replacing it?

## Example interaction ideas

These are examples for inspiration only.

You do not need to copy them.

Examples:

- a timeline reconstruction tool
- a visual relationship map
- a guided reflection conversation
- an AI-assisted note cleanup view
- a hypothesis-testing interaction
- a memory capture flow
- a drag-and-drop reasoning canvas

## What good work looks like

Strong projects usually:

- focus on one clear interaction
- help users understand something new
- make thinking more visible
- reduce confusion or overload
- lead toward meaningful action
- are tested with real users or realistic situation

## Theory background

This project draws on three complementary perspectives from cognitive science and learning theory that together help explain why reflection is difficult and how interaction design can support it. These theories are not used to build a psychological model of reflection, but as design lenses: they help us think about how interfaces, structure, and interaction can either support or interrupt reflective thinking.

In simple terms, the following ideas were taken from these theories:

- **Dewey:** avoid fixed interpretation → the tool should support evolving inquiry
- **Dual-process theory:** avoid immediate conclusions → the tool should support reconsideration and conflict detection
- **Cognitive Load Theory (CLT):** avoid unnecessary mental effort → the tool should support externalized structure and memory

## Reflection as inquiry

**Dewey, J. (1910). How We Think**

In Dewey's view, reflection is not passive thinking but an active process of inquiry grounded in experience. Reflection begins when a person encounters a situation that feels uncertain, incomplete, or confusing. From there, the person starts questioning, interpreting, and revisiting the experience in order to better understand it.

Importantly, reflection is tied to action. The goal is not simply describing what happened, but reorganising experience into something that can guide future decisions and behaviour. Reflection therefore becomes a process of making sense of experience rather than merely recording it.

This perspective is especially relevant to the project because students often describe situations without fully examining why they happened or how they connect to broader patterns over time. The project therefore explores how interaction design can support inquiry rather than just documentation.

**A more modern interpretation:**  
Rodgers, C. (2002). Defining reflection: Another look at John Dewey and reflective thinking. Teachers College Record, 104(4), 842-866.  
<https://journals.sagepub.com/doi/10.1111/1467-9620.00181>

## Dual-process theory and cognitive friction

Dual-process theories of cognition distinguish between fast, intuitive thinking (System 1) and slower, more deliberate reasoning (System 2). Everyday interpretation of experiences often relies on System 1, producing quick but sometimes oversimplified explanations. System 2 is more likely to become engaged when something feels uncertain, conflicting, inconsistent, or effortful.

In this sense, cognitive friction - such as ambiguity, contradiction, or alternative explanations - can trigger deeper reflection by encouraging users to reconsider their initial interpretation rather than accepting it immediately.

For this project, this is important because students may quickly settle on simple explanations without exploring assumptions, evidence, or alternative perspectives. Interaction techniques such as comparison, questioning, visual organisation, or evidence mapping may help support more deliberate reasoning.

At the same time, the theory also suggests that too much friction can become counterproductive if the interaction becomes exhausting or overly complicated.

### Sources

- **Primary source (historical / foundational):**  
   Kahneman, D. (2011). Thinking, Fast and Slow. Farrar, Straus and Giroux.  
   → System 1 = fast intuition, System 2 = effortful reasoning
- **Foundational academic paper:**  
   Stanovich, K. E., & West, R. F. (2000).  
   Individual differences in reasoning: Implications for the rationality debate? Behavioral and Brain Sciences, 23(5), 645-665.  
   → Introduces dual-process distinctions in cognitive psychology
- **Modern interpretation (conflict triggering deeper reasoning):**  
   Evans, J. St. B. T., & Stanovich, K. E. (2013).  
   Dual-process theories of higher cognition: Advancing the debate. Perspectives on Psychological Science, 8(3), 223-241.  
   → System 2 is more likely to engage when conflict, uncertainty, or monitoring demands arise

## Cognitive Load Theory and external support

Cognitive Load Theory emphasises that working memory is limited, and that learning and reasoning suffer when too much mental effort is spent on irrelevant or poorly structured information. The theory distinguishes between:

- **Intrinsic load** → the complexity of the task itself
- **Extraneous load** → unnecessary effort caused by poor design or interaction
- **Germane load** → productive mental effort that supports understanding and learning

For reflection tools, this suggests a need to reduce unnecessary mental effort by offloading memory, externalising structure, and helping users organise information more clearly.

For example, reflection can become difficult if users must simultaneously remember events, organise notes, interpret meaning, and navigate a complex interface. Timelines, visual maps, retrieval systems, and structured overviews may help reduce this burden by making information easier to revisit and interpret.

Importantly, CLT does not suggest removing all difficulty. Reflection still requires effort. The challenge is therefore to reduce unnecessary cognitive burden while preserving the productive effort involved in interpretation and meaning-making.

Here are some questions that can help with increasing the Germane load:

- Ask WHY not only WHAT:
  - Why do you think this approach worked in this situation?
- Go from concrete to abstract:
  - What general rule can you extract from this experience?
- Compare and contrast:
  - How was this situation different from the last time you faced something similar?
- Error Analysis:
  - What assumption turned out to be wrong?
- Make a prediction, and compare with the later outcome:
  - Step 1 (Before): What do you expect will happen? Why?
  - Step 2 (after): Where did your prediction differ from reality?

### Sources

- Sweller, J. (1988).  
   Cognitive load during problem solving: Effects on learning. Cognitive Science, 12(2), 257-285.
- Sweller, J., van Merriënboer, J. J. G., & Paas, F. (2019).  
   Cognitive architecture and instructional design: 20 years later. Educational Psychology Review, 31, 261-292.

## Implications for design

Together, these perspectives suggest that reflective systems must balance three goals:

- supporting open-ended inquiry and meaning-making (Dewey)
- encouraging deeper reasoning when appropriate (dual-process theory)
- reducing unnecessary cognitive burden (CLT)

The design challenge is therefore not simply to "help users reflect," but to balance ease of use with moments of productive difficulty that support interpretation and learning.

### Critical design questions

What would each theory say my design is doing wrong?

- **Dewey** → am I killing inquiry by structuring too early?
- **Dual-process theory** → am I failing to trigger deeper reasoning?