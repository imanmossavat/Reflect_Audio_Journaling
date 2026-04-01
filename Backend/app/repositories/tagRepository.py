from sqlalchemy import func
from sqlmodel import Session, select

from database.models import Journal, JournalTag, Tag, TagCluster




def get_tag_by_name(session: Session, name: str) -> Tag | None:
    return session.exec(select(Tag).where(Tag.name == name.strip().lower())).first()


def get_cluster_by_name(session: Session, name: str) -> TagCluster | None:
    return session.exec(select(TagCluster).where(TagCluster.name == name.strip().lower())).first()


def get_or_create_cluster(session: Session, *, name: str, description: str | None = None) -> TagCluster:
    normalised = name.strip().lower()
    cluster = get_cluster_by_name(session, normalised)
    if not cluster:
        cluster = TagCluster(name=normalised, description=description)
        session.add(cluster)
        session.flush()
    return cluster


def get_tag_by_id(session: Session, tag_id: int) -> Tag | None:
    return session.get(Tag, tag_id)


def get_all_tags(session: Session) -> list[Tag]:
    return session.exec(select(Tag)).all()


def get_or_create_tag(session: Session, *, name: str) -> Tag:
    normalised = name.strip().lower()
    tag = get_tag_by_name(session, normalised)
    if not tag:
        default_cluster = get_or_create_cluster(
            session,
            name="general",
            description="Default cluster for extracted and manual tags",
        )
        tag = Tag(name=normalised, tag_cluster_id=default_cluster.id)
        session.add(tag)
        session.flush()
    return tag




def get_tags_for_journal(session: Session, journal_id: int) -> list[Tag]:
    stmt = (
        select(Tag)
        .join(JournalTag, Tag.id == JournalTag.tag_id)
        .where(JournalTag.journal_id == journal_id)
    )
    return session.exec(stmt).all()


def get_junction(session: Session, journal_id: int, tag_id: int) -> JournalTag | None:
    return session.exec(
        select(JournalTag).where(
            JournalTag.journal_id == journal_id,
            JournalTag.tag_id == tag_id,
        )
    ).first()


def add_tag_to_journal(
    session: Session, *, journal_id: int, tag_id: int, commit: bool = True
) -> bool:
    if get_junction(session, journal_id, tag_id):
        return False
    session.add(JournalTag(journal_id=journal_id, tag_id=tag_id))
    if commit:
        session.commit()
    else:
        session.flush()
    return True


def remove_tag_from_journal(session: Session, *, journal_id: int, tag_id: int) -> bool:
    junction = get_junction(session, journal_id, tag_id)
    if not junction:
        return False
    session.delete(junction)
    session.commit()
    return True




def get_journals_by_tags(
    session: Session,
    *,
    tag_names: list[str],
    match: str = "any",  # "any" (OR) | "all" (AND)
) -> list[Journal]:
    normalised = [n.strip().lower() for n in tag_names if n.strip()]
    if not normalised:
        return []

    if match == "all":
        stmt = (
            select(Journal)
            .join(JournalTag, Journal.id == JournalTag.journal_id)
            .join(Tag, Tag.id == JournalTag.tag_id)
            .where(Tag.name.in_(normalised))
            .group_by(Journal.id)
            .having(func.count(func.distinct(Tag.id)) == len(normalised))
        )
    else:
        stmt = (
            select(Journal)
            .join(JournalTag, Journal.id == JournalTag.journal_id)
            .join(Tag, Tag.id == JournalTag.tag_id)
            .where(Tag.name.in_(normalised))
            .distinct()
        )

    return session.exec(stmt).all()