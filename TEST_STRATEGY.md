# REFLECT — Minimal Test Strategy (P0 only)

Not tests. A blueprint of the highest-ROI additions — each entry is a
name, the invariant it protects, and why it catches a real (not
hypothetical) failure mode. No implementation, no assertions written.

| Test name | Protects | Why it catches a real failure |
|---|---|---|
| `test_reflection_state_concurrent_turns_do_not_lose_updates` | R1 | The system explicitly supports LAN/mobile access to the same backend, so two sessions touching one chat is a supported usage pattern, not an edge case. A lost update currently produces zero diagnostic trail — this is the single highest-value test in the system precisely because nothing else would ever surface it. |
| `test_generate_question_route_persists_state_after_reply_even_on_save_failure` (`TestClient`) | R2, R11 | This exact bug — a persistence failure discarding an already-successful reply — was independently found and fixed at three separate call sites in one day. Two of the three are now tested; this is the route-level third, and it's the outermost layer a real user actually hits. |
| `test_query_stream_and_generation_stream_sse_event_shape` (`TestClient`) | R11 | SSE event framing is a hand-maintained contract with the frontend's stream parser. Nothing verifies it mechanically today, and every regression at this layer to date was found by live use, not by a test — this is the cheapest way to stop repeating that pattern. |
| `test_reprocess_source_removes_both_sql_chunks_and_chroma_vectors` | R5 | This already happened once: reprocessing left orphaned, still-searchable vectors because the SQL delete and the Chroma delete are two independent operations with no transactional tie. The fix closed one instance; nothing stops the same shape of bug from recurring at the next call site that deletes a source. |
| `test_reconnect_after_backend_restart_reports_idle_not_hang` | R7 | The in-memory job registry is the only thing `GenerationProvider`'s reconnect logic trusts. A restart during normal development (hot reload, redeploy) is common enough to hit by accident, not just adversarially — and today the client-visible outcome of hitting it is undefined. |
| `test_unit_query_excludes_chunk_vectors_and_vice_versa` | R4 | Units and chunks share one Chroma collection, separated only by a metadata tag with no structural enforcement. This is the single most likely retrieval bug to be introduced by a change that has nothing to do with retrieval — e.g. an unrelated ingestion change that forgets to tag a new write path. |
| `test_safety_guard_fails_open_on_every_error_mode` (parametrized: model missing / timeout / malformed response) | R12 | Fail-open is a deliberate, counter-instinctive product stance. A well-meaning "harden this error handling" change is the single most plausible way to accidentally invert it, and today only a subset of failure modes are actually exercised by existing tests — the others are unverified assumptions. |
| `test_ingest_pipeline_leaves_a_resumable_state_after_a_mid_pipeline_crash` | R5 / R6 (practical proxy) | The session-per-step design exists specifically so a crash between steps doesn't corrupt or lock the database — but nothing currently verifies the *outcome* of that design: that a source crashed mid-pipeline ends up in a status the requeue-on-restart logic can actually recover, rather than stuck or silently duplicated. |

## Why this list and not a broader one

Every entry above targets a failure mode that is **silent** (no
exception, no red test, no user-visible error at the moment it happens)
and **plausible under real usage** (multi-device access, hot reload,
routine reprocessing) rather than requiring an adversarial trigger. P1
invariants (R3, R6's structural half, R8) are deliberately excluded here
— see `ENFORCEMENT_MAP.md` for why several of them aren't test-shaped
problems in the first place.
