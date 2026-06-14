from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload, telemetry, chat, rag, optimization
from app.database.connection import create_tables
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="SustainAI API V2",
    description="AI Sustainability Reasoning Agent — ABB Accelerator Hackathon",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(upload.router, prefix="/api")
app.include_router(telemetry.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(rag.router)
app.include_router(optimization.router, prefix="/api")



@app.on_event("startup")
def startup():
    try:
        create_tables()
        print("INFO:     SQLite Database tables created/verified.")
    except Exception as e:
        print(f"WARNING:  Database error: {e}")

@app.get("/health")
def health():
    return {"status": "ok", "service": "SustainAI API V2"}

from app.services.config import settings

@app.get("/api/config")
def get_config():
    return {"auto_fix": settings.auto_fix}

@app.post("/api/config/toggle")
def toggle_config(payload: dict):
    if "auto_fix" in payload:
        settings.auto_fix = bool(payload["auto_fix"])
    return {"status": "updated", "auto_fix": settings.auto_fix}

@app.get("/")
def root():
    return {
        "message": "Welcome to SustainAI API V2",
        "docs": "/docs",
        "health": "/health",
    }
