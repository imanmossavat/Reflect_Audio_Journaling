from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.services import chatService, sourceService

router = APIRouter()


class CreateChatRequest(BaseModel):
    title: Optional[str] = None


class RenameChatRequest(BaseModel):
    title: str


class AppendMessageRequest(BaseModel):
    role: str
    text: str
    scale_value: Optional[int] = None
    scale_max: Optional[int] = None
    scale_low_label: Optional[str] = None
    scale_high_label: Optional[str] = None
    model: Optional[str] = None
    gibbs_step: Optional[int] = None


@router.get("/chats", tags=["Chat"])
async def list_chats(session: Session = Depends(get_session)):
    return chatService.list_chats(session)


@router.post("/chats", tags=["Chat"])
async def create_chat(
    payload: CreateChatRequest,
    session: Session = Depends(get_session),
):
    return chatService.create_chat(session, title=payload.title)


@router.get("/chats/{chat_id}", tags=["Chat"])
async def get_chat(chat_id: int, session: Session = Depends(get_session)):
    return chatService.get_chat_with_messages(session, chat_id)


@router.patch("/chats/{chat_id}", tags=["Chat"])
async def rename_chat(
    chat_id: int,
    payload: RenameChatRequest,
    session: Session = Depends(get_session),
):
    return chatService.rename_chat(session, chat_id, payload.title)


@router.delete("/chats/{chat_id}", tags=["Chat"])
async def delete_chat(chat_id: int, session: Session = Depends(get_session)):
    chatService.delete_chat(session, chat_id)
    return {"ok": True}


@router.post("/chats/{chat_id}/messages", tags=["Chat"])
async def append_message(
    chat_id: int,
    payload: AppendMessageRequest,
    session: Session = Depends(get_session),
):
    return chatService.append_message(
        session,
        chat_id,
        role=payload.role,
        text=payload.text,
        scale_value=payload.scale_value,
        scale_max=payload.scale_max,
        scale_low_label=payload.scale_low_label,
        scale_high_label=payload.scale_high_label,
        model=payload.model,
        gibbs_step=payload.gibbs_step,
    )


@router.post("/chats/{chat_id}/promote", tags=["Chat"])
async def promote_chat(
    chat_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    result = chatService.promote_chat(session, chat_id)
    source = result["source"]
    background_tasks.add_task(sourceService._process_source_background, source.id)
    return result


@router.post("/chats/{chat_id}/reindex", tags=["Chat"])
async def reindex_chat(
    chat_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    source = chatService.reindex_chat(session, chat_id)
    background_tasks.add_task(sourceService._process_source_background, source.id)
    return source
