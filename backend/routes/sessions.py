import json
import os
import psycopg2
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

from agent.memory import memory_store

load_dotenv()

router = APIRouter()


# models
class SessionInfo(BaseModel):
    session_id: str
    message_count: int
    preferred_chart_type: Optional[str] = None


# helpers
def get_pg_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        database=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD")
    )


# endpoints
@router.get("/session/{session_id}", response_model=SessionInfo)
def get_session(session_id: str):
    session = memory_store.get_or_create(session_id)
    return SessionInfo(
        session_id=session_id,
        message_count=len(session.messages),
        preferred_chart_type=session.preferred_chart_type
    )


@router.get("/session/{session_id}/messages")
def get_session_messages(session_id: str):
    try:
        conn = get_pg_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT messages FROM chat_sessions WHERE session_id = %s",
            (session_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row is None:
            return {"messages": []}
        msgs = row[0]
        if isinstance(msgs, str):
            msgs = json.loads(msgs)
        return {"messages": msgs}
    except Exception as e:
        return {"messages": [], "error": str(e)}


@router.delete("/session/{session_id}")
def clear_session(session_id: str):
    memory_store.delete(session_id)
    return {"message": f"Session {session_id} cleared"}


@router.get("/sessions")
def list_sessions():
    return {"sessions": memory_store.list_sessions()}