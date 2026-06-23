from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from database.models import Chat, ChatMessage


def create_chat(session: Session, *, title: str = "Untitled") -> Chat:
    now = datetime.now()
    chat = Chat(title=title, created_at=now, edited_at=now)
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def get_chat_by_id(session: Session, chat_id: int) -> Optional[Chat]:
    return session.exec(select(Chat).where(Chat.id == chat_id)).first()


def list_chats(session: Session) -> list[dict]:
    rows = session.exec(
        select(
            Chat,
            func.count(ChatMessage.id).label("message_count"),
        )
        .outerjoin(ChatMessage, ChatMessage.chat_id == Chat.id)
        .group_by(Chat.id)
        .order_by(Chat.edited_at.desc())
    ).all()

    chats: list[dict] = []
    for chat, message_count in rows:
        chats.append({
            "id": chat.id,
            "title": chat.title,
            "source_id": chat.source_id,
            "reflection_goal": chat.reflection_goal,
            "reflection_scope": chat.reflection_scope,
            "message_count": int(message_count or 0),
            "edited_at": chat.edited_at,
            "created_at": chat.created_at,
        })
    return chats


def get_messages(session: Session, chat_id: int) -> list[ChatMessage]:
    return session.exec(
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    ).all()


def update_chat_title(session: Session, chat: Chat, title: str) -> Chat:
    chat.title = title
    chat.edited_at = datetime.now()
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def set_reflection_goal(session: Session, chat: Chat, goal: Optional[str]) -> Chat:
    chat.reflection_goal = goal
    chat.edited_at = datetime.now()
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def set_reflection_scope(session: Session, chat: Chat, scope: Optional[dict]) -> Chat:
    chat.reflection_scope = scope
    chat.edited_at = datetime.now()
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def set_chat_source_id(session: Session, chat: Chat, source_id: Optional[int]) -> Chat:
    chat.source_id = source_id
    chat.edited_at = datetime.now()
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def touch_chat(session: Session, chat: Chat) -> Chat:
    chat.edited_at = datetime.now()
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def delete_chat(session: Session, chat: Chat) -> None:
    messages = session.exec(
        select(ChatMessage).where(ChatMessage.chat_id == chat.id)
    ).all()
    for message in messages:
        session.delete(message)
    session.delete(chat)
    session.commit()


def append_message(
    session: Session,
    *,
    chat_id: int,
    role: str,
    text: str,
    scale_value: Optional[int] = None,
    scale_max: Optional[int] = None,
    scale_low_label: Optional[str] = None,
    scale_high_label: Optional[str] = None,
    model: Optional[str] = None,
    thinking: Optional[str] = None,
    gibbs_step: Optional[int] = None,
    sources: Optional[list] = None,
) -> ChatMessage:
    message = ChatMessage(
        chat_id=chat_id,
        role=role,
        text=text,
        scale_value=scale_value,
        scale_max=scale_max,
        scale_low_label=scale_low_label,
        scale_high_label=scale_high_label,
        model=model,
        thinking=thinking,
        gibbs_step=gibbs_step,
        sources=sources,
        created_at=datetime.now(),
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def delete_chunks_for_source(session: Session, source_id: int) -> int:
    from database.models import Chunk

    chunks = session.exec(select(Chunk).where(Chunk.source_id == source_id)).all()
    count = len(chunks)
    for chunk in chunks:
        session.delete(chunk)
    session.commit()
    return count
