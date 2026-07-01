"""Repository-level tests for SourceTag.origin provenance writes.

See docs/DB_TESTING_PROPOSAL.md. Added in the same pass as
test_source_provenance.py rather than later: tags, summaries, and
transcripts are being retrofitted onto the same provenance shape together
(per Document B's build order), so their write-path tests belong together
too, not staggered across separate sessions.
"""
import pytest

from database.models import Source, Tag
from app.repositories import tagRepository


def _make_source_and_tag(session, tag_name="focus"):
    source = Source()
    tag = Tag(name=tag_name)
    session.add(source)
    session.add(tag)
    session.commit()
    session.refresh(source)
    session.refresh(tag)
    return source, tag


# ---------------------------------------------------------------------------
# origin defaulting / explicit setting
# ---------------------------------------------------------------------------

def test_add_tag_to_source_defaults_to_user_origin(session):
    source, tag = _make_source_and_tag(session)

    tagRepository.add_tag_to_source(session, source_id=source.id, tag_id=tag.id)

    links = tagRepository.get_tags_for_source(session, source.id)
    assert [t.name for t in links] == ["focus"]
    junction = tagRepository.get_junction(session, source.id, tag.id)
    assert junction.origin == "user"


def test_add_tag_to_source_accepts_explicit_llm_origin(session):
    source, tag = _make_source_and_tag(session)

    tagRepository.add_tag_to_source(session, source_id=source.id, tag_id=tag.id, origin="llm")

    junction = tagRepository.get_junction(session, source.id, tag.id)
    assert junction.origin == "llm"


# ---------------------------------------------------------------------------
# clear_llm_tags_for_source: the merge-adjacent filter logic worth guarding,
# same spirit as the derived_meta clobber tests -- removing the wrong set of
# rows here would silently delete a user's manual tags on every re-extract.
# ---------------------------------------------------------------------------

def test_clear_llm_tags_removes_only_llm_origin_and_preserves_user_tags(session):
    source = Source()
    user_tag = Tag(name="user-added")
    llm_tag = Tag(name="llm-suggested")
    session.add(source)
    session.add(user_tag)
    session.add(llm_tag)
    session.commit()
    session.refresh(source)
    session.refresh(user_tag)
    session.refresh(llm_tag)

    tagRepository.add_tag_to_source(session, source_id=source.id, tag_id=user_tag.id, origin="user")
    tagRepository.add_tag_to_source(session, source_id=source.id, tag_id=llm_tag.id, origin="llm")

    removed = tagRepository.clear_llm_tags_for_source(session, source.id)

    assert removed == 1
    remaining = {t.name for t in tagRepository.get_tags_for_source(session, source.id)}
    assert remaining == {"user-added"}


# ---------------------------------------------------------------------------
# Known, documented limitation (docs/ISSUES.md #15) -- pinned as current
# behavior, not xfail: there is no confirmed "correct" shape to assert
# toward yet (that's the upcoming provenance work). This test exists so the
# behavior doesn't silently change underneath that future decision.
# ---------------------------------------------------------------------------

def test_confirmed_llm_suggestion_is_indistinguishable_from_a_manual_tag(session):
    """docs/ISSUES.md #15: the suggest -> confirm flow (routes/tags.py
    confirm_suggested_tags) calls add_tag_to_source with no origin=
    argument, so a user-approved LLM suggestion is persisted identically to
    a hand-typed tag. This pins that today's origin value is "user" in
    both cases -- i.e. that history is already unrecoverable -- so a future
    fix has to be a schema/flow change, not something a repository test
    could have caught after the fact.
    """
    source, tag = _make_source_and_tag(session, tag_name="confirmed-suggestion")

    # Mirrors routes/tags.py's confirm_suggested_tags: no origin kwarg passed.
    tagRepository.add_tag_to_source(session, source_id=source.id, tag_id=tag.id)

    manual_junction = tagRepository.get_junction(session, source.id, tag.id)
    assert manual_junction.origin == "user"
