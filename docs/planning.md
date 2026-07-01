**Legend:** `[x]` done · `(*)` greenlit but needs a more mature design first · everything else is greenlit and straightforward (build as-is).

**High**

- [x] Redesign input area around three action levers: Reflect, Ask Sources, Continue
      (was "Continue to Evaluation" — really means advance to the next Gibbs stage)
- [x] Drop the "X of 6" progress counter
- [x] Move Promote to Source into the chat context menu (active chat's top-bar menu)
- [ ] Shorten and simplify AI question phrasing (*) (prototype in Research/Reflection eval first)
- [ ] Add multiple-choice question options (*)
- [x] Resolve unanswered-question flow via Continue (advancing records the current answer, if any)

**Medium**

- [ ] Add Verified/Unverified state for source summaries (really High priority)
- [ ] Enable direct summary editing with redaction support (*)
      (decision for now: if the user modifies it, treat the modified version as an edited AI entry)
- [ ] Add clickable source citations (*)
- [ ] Add Duplicate as Note for full source editing
- [x] Add Copy Text button to source panels (Summary + Transcript/Text)
- [ ] Add explicit Validate AI Ingestion step (*)

**Low**

- [x] Show model size and memory requirement on Whisper settings
- [ ] Move database folder out of backend directory
- [ ] Add User Note field using two calls instead of two layers (?)
