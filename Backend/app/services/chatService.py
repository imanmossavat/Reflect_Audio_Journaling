from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session

from app import logging_config
from app.db import engine
from app.repositories import chatRepository, sourceRepository
from app.services.chroma import get_chroma_collection
from database.models import Chat

logger = logging_config.logger


PROCESSING_STATUSES = {"queued", "transcribing", "chunking", "indexing"}


def list_chats(session: Session) -> list[dict]:
    return chatRepository.list_chats(session)


def get_chat_with_messages(session: Session, chat_id: int) -> dict:
    chat = chatRepository.get_chat_by_id(session, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    messages = chatRepository.get_messages(session, chat_id)
    return {
        "id": chat.id,
        "title": chat.title,
        "source_id": chat.source_id,
        "reflection_goal": chat.reflection_goal,
        "reflection_scope": chat.reflection_scope,
        "created_at": chat.created_at,
        "edited_at": chat.edited_at,
        "messages": messages,
    }


def create_chat(session: Session, *, title: Optional[str] = None) -> Chat:
    return chatRepository.create_chat(session, title=title or "Untitled")


def rename_chat(session: Session, chat_id: int, title: str) -> Chat:
    chat = chatRepository.get_chat_by_id(session, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    clean = (title or "").strip()
    if not clean:
        raise HTTPException(status_code=400, detail="Title cannot be empty.")
    return chatRepository.update_chat_title(session, chat, clean[:255])


def update_reflection_goal(session: Session, chat_id: int, goal: Optional[str]) -> Chat:
    chat = chatRepository.get_chat_by_id(session, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    clean = (goal or "").strip()
    return chatRepository.set_reflection_goal(session, chat, clean or None)


def update_reflection_scope(session: Session, chat_id: int, scope: Optional[dict]) -> Chat:
    chat = chatRepository.get_chat_by_id(session, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    # An empty scope (no items and no topic) is stored as None.
    if scope and (scope.get("items") or scope.get("topic")):
        return chatRepository.set_reflection_scope(session, chat, scope)
    return chatRepository.set_reflection_scope(session, chat, None)


def delete_chat(session: Session, chat_id: int) -> None:
    chat = chatRepository.get_chat_by_id(session, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    chatRepository.delete_chat(session, chat)


def _derive_title_from_text(text: str) -> str:
    flattened = " ".join(text.split())
    return flattened[:60] if flattened else "Untitled"


def append_message(
    session: Session,
    chat_id: int,
    *,
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
) -> dict:
    if role not in ("question", "answer"):
        raise HTTPException(status_code=400, detail="role must be 'question' or 'answer'.")
    if not (text or "").strip():
        raise HTTPException(status_code=400, detail="text cannot be empty.")

    chat = chatRepository.get_chat_by_id(session, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")

    message = chatRepository.append_message(
        session,
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
    )
    # Snapshot the fresh row before subsequent commits expire its attributes.
    snapshot = message.model_dump()

    if chat.title == "Untitled" and role == "answer":
        chatRepository.update_chat_title(session, chat, _derive_title_from_text(text))
    else:
        chatRepository.touch_chat(session, chat)

    return snapshot


def serialize_chat_to_markdown(session: Session, chat_id: int) -> str:
    messages = chatRepository.get_messages(session, chat_id)
    if not messages:
        return ""

    blocks: list[str] = []
    pending_question: Optional[str] = None

    for message in messages:
        if message.role == "question":
            pending_question = message.text.strip()
            continue

        # role == "answer"
        if message.scale_value is not None:
            scale_max = message.scale_max or 10
            answer_text = f"{message.scale_value}/{scale_max}"
        else:
            answer_text = message.text.strip()

        question_part = f"**Q:** {pending_question}\n\n" if pending_question else ""
        blocks.append(f"{question_part}**A:** {answer_text}")
        pending_question = None

    if pending_question:
        blocks.append(f"**Q:** {pending_question}")

    return "\n\n---\n\n".join(blocks)


def promote_chat(session: Session, chat_id: int):
    chat = chatRepository.get_chat_by_id(session, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    if chat.source_id is not None:
        raise HTTPException(status_code=400, detail="Chat is already saved as a source. Use update source instead.")

    markdown = serialize_chat_to_markdown(session, chat_id)
    if not markdown.strip():
        raise HTTPException(status_code=400, detail="Chat has no content to promote.")

    title = chat.title if chat.title and chat.title != "Untitled" else _derive_title_from_text(markdown)

    source = sourceRepository.create_source(
        session=session,
        filename=title,
        file_type="chat",
        text=markdown,
        status="queued",
    )

    chatRepository.set_chat_source_id(session, chat, source.id)
    return {"chat": chatRepository.get_chat_by_id(session, chat_id), "source": source}


def reindex_chat(session: Session, chat_id: int):
    chat = chatRepository.get_chat_by_id(session, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    if chat.source_id is None:
        raise HTTPException(status_code=400, detail="Chat has not been promoted yet.")

    source = sourceRepository.get_source_by_id(session, chat.source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Linked source not found.")
    if source.status in PROCESSING_STATUSES:
        raise HTTPException(status_code=409, detail="Source is currently processing.")

    markdown = serialize_chat_to_markdown(session, chat_id)
    if not markdown.strip():
        raise HTTPException(status_code=400, detail="Chat has no content to index.")

    # Wipe old chunks and vector entries before re-running the pipeline
    deleted = chatRepository.delete_chunks_for_source(session, source.id)
    if deleted:
        try:
            collection = get_chroma_collection()
            collection.delete(where={"source_id": str(source.id)})
        except Exception as exc:
            logger.error(f"Chroma delete for source {source.id} failed — vectors orphaned: {exc}")

    sourceRepository.update_source_text(session, source, markdown)
    updated_source = sourceRepository.update_source_status(session, source, "queued")

    chatRepository.touch_chat(session, chat)
    return updated_source
