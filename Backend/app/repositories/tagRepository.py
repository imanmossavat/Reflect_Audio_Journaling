from sqlalchemy import func
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload, load_only

from database.models import Source, SourceTag, Tag




def get_tag_by_name(session: Session, name: str) -> Tag | None:
    return session.exec(select(Tag).where(Tag.name == name.strip().lower())).first()


def get_tag_by_id(session: Session, tag_id: int) -> Tag | None:
    return session.get(Tag, tag_id)


def get_all_tags(session: Session) -> list[Tag]:
    return session.exec(select(Tag)).all()


def get_all_tags_with_sources(session: Session) -> list[Tag]:
    stmt = (
        select(Tag)
        .options(
            selectinload(Tag.sources).load_only(
                Source.id,
                Source.filename,
                Source.file_type,
            )
        )
        .order_by(Tag.name)
    )
    return session.exec(stmt).all()


def get_or_create_tag(session: Session, *, name: str) -> Tag:
    normalised = name.strip().lower()
    tag = get_tag_by_name(session, normalised)
    if not tag:
        tag = Tag(name=normalised)
        session.add(tag)
        session.flush()
    return tag




def get_tags_for_source(session: Session, source_id: int) -> list[Tag]:
    stmt = (
        select(Tag)
        .join(SourceTag, Tag.id == SourceTag.tag_id)
        .where(SourceTag.source_id == source_id)
    )
    return session.exec(stmt).all()


def get_junction(session: Session, source_id: int, tag_id: int) -> SourceTag | None:
    return session.exec(
        select(SourceTag).where(
            SourceTag.source_id == source_id,
            SourceTag.tag_id == tag_id,
        )
    ).first()


def add_tag_to_source(
    session: Session, *, source_id: int, tag_id: int, origin: str = "user", commit: bool = True
) -> bool:
    if get_junction(session, source_id, tag_id):
        return False
    session.add(SourceTag(source_id=source_id, tag_id=tag_id, origin=origin))
    if commit:
        session.commit()
    else:
        session.flush()
    return True


def clear_llm_tags_for_source(session: Session, source_id: int, *, commit: bool = True) -> int:
    """Remove only the auto-extracted (origin="llm") tag links for a source.

    Used before re-extracting so a recompute refreshes LLM tags without touching the
    user's manual ("user") tags. Returns how many links were removed.
    """
    links = session.exec(
        select(SourceTag).where(
            SourceTag.source_id == source_id,
            SourceTag.origin == "llm",
        )
    ).all()
    for link in links:
        session.delete(link)
    if commit:
        session.commit()
    else:
        session.flush()
    return len(links)


def remove_tag_from_source(session: Session, *, source_id: int, tag_id: int) -> bool:
    junction = get_junction(session, source_id, tag_id)
    if not junction:
        return False
    session.delete(junction)
    session.commit()
    return True




def get_sources_by_tags(
    session: Session,
    *,
    tag_names: list[str],
    match: str = "any",  # "any" (OR) | "all" (AND)
) -> list[Source]:
    normalised = [n.strip().lower() for n in tag_names if n.strip()]
    if not normalised:
        return []

    if match == "all":
        stmt = (
            select(Source)
            .join(SourceTag, Source.id == SourceTag.source_id)
            .join(Tag, Tag.id == SourceTag.tag_id)
            .where(Tag.name.in_(normalised))
            .group_by(Source.id)
            .having(func.count(func.distinct(Tag.id)) == len(normalised))
        )
    else:
        stmt = (
            select(Source)
            .join(SourceTag, Source.id == SourceTag.source_id)
            .join(Tag, Tag.id == SourceTag.tag_id)
            .where(Tag.name.in_(normalised))
            .distinct()
        )

    return session.exec(stmt).all()