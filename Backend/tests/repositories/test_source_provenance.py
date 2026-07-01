"""Repository-level tests for Source.derived_meta provenance writes.

See docs/DB_TESTING_PROPOSAL.md. Two distinct failure modes are covered,
deliberately kept as separate tests:

1. The hypothetical merge-clobber bug: one derived_meta write accidentally
   overwriting the whole dict instead of merging into it, wiping out a
   sibling artifact's provenance.
2. The real, confirmed bug (docs/ISSUES.md #12): editing summary/transcript
   text through the normal manual-edit path never touches derived_meta at
   all, so the stamp keeps asserting the original AI generation as if
   untouched.
"""
import pytest

from database.models import Source
from app.repositories import sourceRepository


# ---------------------------------------------------------------------------
# 1. Merge logic: writing one artifact's provenance must not clobber another's
# ---------------------------------------------------------------------------

def test_update_source_transcript_preserves_existing_summary_meta(session):
    source = Source(derived_meta={"summary": {"model": "gemma4"}})
    session.add(source)
    session.commit()

    sourceRepository.update_source_transcript(
        session, source, "transcript text", [], provenance={"model": "medium"}
    )

    assert source.derived_meta["summary"] == {"model": "gemma4"}
    assert source.derived_meta["transcript"] == {"model": "medium"}


def test_update_source_summary_preserves_existing_transcript_meta(session):
    source = Source(derived_meta={"transcript": {"model": "medium", "device": "cpu"}})
    session.add(source)
    session.commit()

    sourceRepository.update_source_summary(
        session, source, "a new summary", provenance={"model": "gemma4"}
    )

    assert source.derived_meta["transcript"] == {"model": "medium", "device": "cpu"}
    assert source.derived_meta["summary"] == {"model": "gemma4"}


# ---------------------------------------------------------------------------
# 2. The real bug: a manual edit must not leave a stale AI-provenance stamp
#
# xfail(strict=True): this must start failing (XPASS) the moment
# update_source_fields is fixed to actually address the stamp -- at which
# point this test should be rewritten to assert whatever that fix produces,
# rather than just "not the stale value" (kept deliberately loose here so it
# doesn't presume the shape of the eventual provenance retrofit).
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason="docs/ISSUES.md #12 -- update_source_fields never touches derived_meta on manual edit",
)
def test_manual_summary_edit_updates_stale_provenance_stamp(session):
    stale_stamp = {"model": "gemma4", "prompt_version": 1, "generated_at": "2026-06-01T00:00:00"}
    source = Source(summary="original AI-generated summary", derived_meta={"summary": stale_stamp})
    session.add(source)
    session.commit()

    sourceRepository.update_source_fields(session, source, summary="hand-edited by a human")

    assert source.summary == "hand-edited by a human"
    # Today this is still exactly `stale_stamp` -- the bug. Once fixed, it
    # must no longer equal the pre-edit stamp in some form (cleared,
    # replaced, flagged -- whatever the provenance retrofit decides).
    assert source.derived_meta.get("summary") != stale_stamp


@pytest.mark.xfail(
    strict=True,
    reason="docs/ISSUES.md #12 -- update_source_fields never touches derived_meta on manual edit",
)
def test_manual_text_edit_updates_stale_transcript_provenance_stamp(session):
    stale_stamp = {"model": "medium", "device": "cuda", "duration_s": 12.3}
    source = Source(text="original transcribed text", derived_meta={"transcript": stale_stamp})
    session.add(source)
    session.commit()

    sourceRepository.update_source_fields(session, source, text="hand-edited transcript")

    assert source.text == "hand-edited transcript"
    assert source.derived_meta.get("transcript") != stale_stamp
