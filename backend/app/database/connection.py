from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os

REPO_ROOT = Path(__file__).resolve().parents[3]
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{REPO_ROOT / 'sustainai.db'}")

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    from app.database import models
    models.Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()


def _apply_lightweight_migrations():
    """Keep local SQLite demo databases compatible with evolving models."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    migrations = {
        "agent_logs": {
            "device": "ALTER TABLE agent_logs ADD COLUMN device VARCHAR(100)",
        },
        "recommendations": {
            "reasoning_proof": "ALTER TABLE recommendations ADD COLUMN reasoning_proof TEXT",
            "control_action": "ALTER TABLE recommendations ADD COLUMN control_action VARCHAR(200)",
        },
        "session_reports": {},
    }

    with engine.begin() as conn:
        for table, columns in migrations.items():
            if table not in table_names:
                continue
            existing = {col["name"] for col in inspector.get_columns(table)}
            for column, statement in columns.items():
                if column not in existing:
                    conn.execute(text(statement))
