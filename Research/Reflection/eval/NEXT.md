# START HERE — stateful facilitator, Phase 2

## Where we are
State core + extraction call + multi-turn session replay all built in `harness/`.
Tests green: `python harness/test_state.py` (22/22), `python harness/test_turn.py` (5/5).

Two gate bugs found via session replay and fixed (2026-07-01, see FINDINGS top entry):
- Description gate loosened (`>=2 facts + (domain OR project_type)`).
- `check_advance_confirmation` -> whole-word match (raw substring advanced on "ok" inside "broken").

Latest run (`run_session.py --temperature 0`, gemma4:e4b) walks **Description -> Feelings ->
Evaluation**, advancing only on the real confirm turns.

## Open decision — how to make stage gates robust (don't grow keyword lists)
Keyword gates are brittle: "went well" misses "went really well". Options:
1. Gate on fact-count + a model-set per-stage "covered" flag we sanity-check (less keyword reliance).
2. Extend the dataset so all 6 stages are reachable (S1 stops at Evaluation) + add a
   thin/off-topic/resistance session.
3. Add an LLM judge over `facts` for the emotion-labeling axis.

## Residual bugs (logged, not fixed)
- "sure" in "not sure"/"make sure" still reads as consent.
- multi-word "move on" ⊂ "remove one".

## Re-run
```
python harness/test_state.py && python harness/test_turn.py
python harness/run_session.py --temperature 0
```
Full context: `FINDINGS.md` (top entries).
