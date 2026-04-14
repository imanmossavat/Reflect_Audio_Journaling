from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

from app.db import get_session
from database.models import Source
from app.repositories import tagRepository as repo
from app.schemas.tagSchemas import (
    TagCreate,
    TagRead,
    TagSuggestionsResponse,
    BulkTagConfirm,
)
from app.services.tagService import suggest_tags_via_llm

router = APIRouter(prefix="/sources/{source_id}/tags", tags=["tags"])




@router.get("", response_model=List[TagRead])
def list_tags_for_source(source_id: int, session: Session = Depends(get_session)):
    if not session.get(Source, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    return repo.get_tags_for_source(session, source_id)


@router.post("", response_model=TagRead, status_code=201)
def add_tag_to_source(
    source_id: int,
    body: TagCreate,
    session: Session = Depends(get_session),
):
    if not session.get(Source, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    tag = repo.get_or_create_tag(session, name=body.name)
    repo.add_tag_to_source(session, source_id=source_id, tag_id=tag.id)
    return tag


@router.delete("/{tag_id}", status_code=204)
def remove_tag_from_source(
    source_id: int,
    tag_id: int,
    session: Session = Depends(get_session),
):
    removed = repo.remove_tag_from_source(session, source_id=source_id, tag_id=tag_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Tag not applied to this source")




@router.get("/suggest", response_model=TagSuggestionsResponse)
def suggest_tags(source_id: int, session: Session = Depends(get_session)):
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if not source.text:
        raise HTTPException(status_code=422, detail="Source has no text to analyse yet")
    suggestions = suggest_tags_via_llm(source.text)
    return TagSuggestionsResponse(suggestions=suggestions)


@router.post("/suggest/confirm", response_model=List[TagRead], status_code=201)
def confirm_suggested_tags(
    source_id: int,
    body: BulkTagConfirm,
    session: Session = Depends(get_session),
):
    if not session.get(Source, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    saved = []
    try:
        for name in body.names:
            tag = repo.get_or_create_tag(session, name=name)
            repo.add_tag_to_source(
                session,
                source_id=source_id,
                tag_id=tag.id,
                commit=False,
            )
            saved.append(tag)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return saved




search_router = APIRouter(prefix="/sources", tags=["tags"])


@search_router.get("/search", response_model=list)
def search_sources_by_tags(
    tags: str = "",
    match: str = "any",
    session: Session = Depends(get_session),
):
    """
    ?tags=stress,procrastination          → sources with ANY of these tags
    ?tags=stress,procrastination&match=all → sources with ALL of these tags
    """
    if not tags:
        raise HTTPException(status_code=400, detail="Provide at least one tag")
    tag_names = [t.strip() for t in tags.split(",") if t.strip()]
    return repo.get_sources_by_tags(session, tag_names=tag_names, match=match)