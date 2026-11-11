from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from paperlens.auth.dependencies import get_current_user
from paperlens.db.database import get_db
from paperlens.db.models import User, ChatSession, ChatMessage

router = APIRouter(prefix="/chats", tags=["chats"])


# Chat step: find one chat of the logged-in user, or stop with 404 (never reveal other users' chats)
def find_chat(db, chat_id, user):
    chat_session = db.get(ChatSession, chat_id)

    if chat_session is None or chat_session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Chat not found")

    return chat_session


# Chat step: list the chats of the logged-in user, the newest first
@router.get("")
def list_chats(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    rows = (
        db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == current_user.id)
            .order_by(ChatSession.updated_at.desc())
        )
        .scalars()
        .all()
    )

    chats = []
    for row in rows:
        chats.append(
            {"id": row.id, "title": row.title, "updated_at": row.updated_at.isoformat()}
        )

    return {"chats": chats}


# Chat step: open one chat with all its messages
@router.get("/{chat_id}")
def open_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat_session = find_chat(db, chat_id, current_user)

    rows = (
        db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == chat_session.id)
            .order_by(ChatMessage.id)
        )
        .scalars()
        .all()
    )

    messages = []
    for row in rows:
        messages.append({"role": row.role, "content": row.content, "data": row.data})

    return {"id": chat_session.id, "title": chat_session.title, "messages": messages}


# Chat step: delete one chat with all its messages
@router.delete("/{chat_id}")
def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat_session = find_chat(db, chat_id, current_user)

    db.delete(chat_session)
    db.commit()

    return {"deleted": chat_id}
