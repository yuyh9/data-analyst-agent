import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.core import chat

router = APIRouter()


# models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    session_id: str
    chart_url: Optional[str] = None
    report_url: Optional[str] = None
    tables_used: list[str] = []


# endpoints
@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    try:
        result = chat(req.message, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    chart_url = None
    if result.get("chart_filepath"):
        filename = Path(result["chart_filepath"]).name
        chart_url = f"/charts/{filename}"

    report_url = None
    if result.get("report_filepath"):
        filename = Path(result["report_filepath"]).name
        report_url = f"/reports/{filename}"

    return ChatResponse(
        answer=result["answer"],
        session_id=session_id,
        chart_url=chart_url,
        report_url=report_url,
        tables_used=result.get("tables_used", [])
    )