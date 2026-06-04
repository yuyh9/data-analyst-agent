import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from agent.core import initialize
from routes.chat import router as chat_router
from routes.sessions import router as sessions_router
from routes.tables import router as tables_router
from routes.upload import router as upload_router

load_dotenv()

app = FastAPI(title="Data Analyst Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# serve charts
CHARTS_DIR = Path("data/charts")
CHARTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/charts", StaticFiles(directory=str(CHARTS_DIR)), name="charts")

# serve reports as static (for preview)
REPORTS_DIR = Path("data/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")

# routers
app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(tables_router)
app.include_router(upload_router)


# force download endpoint
@app.get("/download/report/{filename}")
def download_report(filename: str):
    filepath = REPORTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    media_type = "application/octet-stream"
    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type=media_type
    )


# startup
@app.on_event("startup")
async def startup():
    print("Initializing agent...")
    initialize()
    print("API ready.")


# health
@app.get("/health")
def health():
    return {"status": "ok", "message": "Data analyst agent is running"}