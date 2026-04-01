from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

from app.db import get_session
from database.models import Journal
from app.repositories import tagRepository as repo
from app.schemas.tagSchemas import (
    TagCreate,
    TagRead,
    TagSuggestionsResponse,
    BulkTagConfirm,
)
from app.services.tagService import suggest_tags_via_llm

router = APIRouter(prefix="/journals/{journal_id}/tags", tags=["tags"])




@router.get("", response_model=List[TagRead])
def list_tags_for_journal(journal_id: int, session: Session = Depends(get_session)):
    if not session.get(Journal, journal_id):
        raise HTTPException(status_code=404, detail="Journal not found")
    return repo.get_tags_for_journal(session, journal_id)


@router.post("", response_model=TagRead, status_code=201)
def add_tag_to_journal(
    journal_id: int,
    body: TagCreate,
    session: Session = Depends(get_session),
):
    if not session.get(Journal, journal_id):
        raise HTTPException(status_code=404, detail="Journal not found")
    tag = repo.get_or_create_tag(session, name=body.name)
    repo.add_tag_to_journal(session, journal_id=journal_id, tag_id=tag.id)
    return tag


@router.delete("/{tag_id}", status_code=204)
def remove_tag_from_journal(
    journal_id: int,
    tag_id: int,
    session: Session = Depends(get_session),
):
    removed = repo.remove_tag_from_journal(session, journal_id=journal_id, tag_id=tag_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Tag not applied to this journal")




@router.get("/suggest", response_model=TagSuggestionsResponse)
def suggest_tags(journal_id: int, session: Session = Depends(get_session)):
    journal = session.get(Journal, journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    if not journal.text:
        raise HTTPException(status_code=422, detail="Journal has no text to analyse yet")
    suggestions = suggest_tags_via_llm(journal.text)
    return TagSuggestionsResponse(suggestions=suggestions)


@router.post("/suggest/confirm", response_model=List[TagRead], status_code=201)
def confirm_suggested_tags(
    journal_id: int,
    body: BulkTagConfirm,
    session: Session = Depends(get_session),
):
    if not session.get(Journal, journal_id):
        raise HTTPException(status_code=404, detail="Journal not found")
    saved = []
    try:
        for name in body.names:
            tag = repo.get_or_create_tag(session, name=name)
            repo.add_tag_to_journal(
                session,
                journal_id=journal_id,
                tag_id=tag.id,
                commit=False,
            )
            saved.append(tag)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return saved




search_router = APIRouter(prefix="/journals", tags=["tags"])


@search_router.get("/search", response_model=list)
def search_journals_by_tags(
    tags: str = "",
    match: str = "any",
    session: Session = Depends(get_session),
):
    """
    ?tags=stress,procrastination          → journals with ANY of these tags
    ?tags=stress,procrastination&match=all → journals with ALL of these tags
    """
    if not tags:
        raise HTTPException(status_code=400, detail="Provide at least one tag")
    tag_names = [t.strip() for t in tags.split(",") if t.strip()]
    return repo.get_journals_by_tags(session, tag_names=tag_names, match=match)