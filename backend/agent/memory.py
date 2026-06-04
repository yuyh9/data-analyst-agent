import json
import os
import psycopg2
import psycopg2.extras
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


# models

@dataclass
class Message:
    role: str
    content: str

@dataclass
class SessionMemory:
    session_id: str
    messages: list[Message] = field(default_factory=list)
    preferred_chart_type: Optional[str] = None
    last_tables_used: list[str] = field(default_factory=list)

    def add_user_message(self, content: str):
        self.messages.append(Message(role="user", content=content))

    def add_assistant_message(self, content: str):
        self.messages.append(Message(role="assistant", content=content))

    def to_openai_format(self) -> list[dict]:
        return [
            {"role": m.role, "content": m.content}
            for m in self.messages
        ]

    def update_chart_preference(self, chart_type: str):
        self.preferred_chart_type = chart_type

    def clear(self):
        self.messages = []
        self.preferred_chart_type = None
        self.last_tables_used = []


# database

def get_pg_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        database=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD")
    )


# store

class MemoryStore:
    """
    Persistent session memory backed by PostgreSQL.
    Each session is a row in chat_sessions table.
    Falls back to in-memory if DB is unavailable.
    """

    def __init__(self):
        self._cache: dict[str, SessionMemory] = {}

    def _load_from_db(self, session_id: str) -> Optional[SessionMemory]:
        try:
            conn = get_pg_conn()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT * FROM chat_sessions WHERE session_id = %s",
                (session_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row is None:
                return None

            session = SessionMemory(session_id=session_id)
            raw_messages = row["messages"]
            if isinstance(raw_messages, str):
                raw_messages = json.loads(raw_messages)
            session.messages = [
                Message(role=m["role"], content=m["content"])
                for m in raw_messages
            ]
            session.preferred_chart_type = row["preferred_chart_type"]
            raw_tables = row["last_tables_used"]
            if isinstance(raw_tables, str):
                raw_tables = json.loads(raw_tables)
            session.last_tables_used = raw_tables or []
            return session

        except Exception as e:
            print(f"Memory load error: {e}")
            return None

    def _save_to_db(self, session: SessionMemory):
        try:
            conn = get_pg_conn()
            cursor = conn.cursor()
            messages_json = json.dumps([
                {"role": m.role, "content": m.content}
                for m in session.messages
            ])
            cursor.execute("""
                INSERT INTO chat_sessions
                    (session_id, messages, preferred_chart_type, last_tables_used, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (session_id) DO UPDATE SET
                    messages = EXCLUDED.messages,
                    preferred_chart_type = EXCLUDED.preferred_chart_type,
                    last_tables_used = EXCLUDED.last_tables_used,
                    updated_at = NOW()
            """, (
                session.session_id,
                messages_json,
                session.preferred_chart_type,
                json.dumps(session.last_tables_used)
            ))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Memory save error: {e}")

    def get_or_create(self, session_id: str) -> SessionMemory:
        # check in-memory cache first
        if session_id in self._cache:
            return self._cache[session_id]

        # try loading from PostgreSQL
        session = self._load_from_db(session_id)
        if session is None:
            session = SessionMemory(session_id=session_id)

        self._cache[session_id] = session
        return session

    def save(self, session_id: str):
        """Call this after each turn to persist to PostgreSQL."""
        if session_id in self._cache:
            self._save_to_db(self._cache[session_id])

    def delete(self, session_id: str):
        self._cache.pop(session_id, None)
        try:
            conn = get_pg_conn()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM chat_sessions WHERE session_id = %s",
                (session_id,)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Memory delete error: {e}")

    def list_sessions(self) -> list[str]:
        try:
            conn = get_pg_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT session_id FROM chat_sessions ORDER BY updated_at DESC"
            )
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return [row[0] for row in rows]
        except Exception as e:
            print(f"Memory list error: {e}")
            return list(self._cache.keys())


# global singleton
memory_store = MemoryStore()