import threading
import logging
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from app.database.connection import get_db
try:
    from rag.retriever import retriever
    from rag.ingest import run_ingestion_pipeline
except ModuleNotFoundError:
    from backend.rag.retriever import retriever
    from backend.rag.ingest import run_ingestion_pipeline

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/rag", tags=["Retrieval Augmented Intelligence"])

@router.post("/ingest")
def trigger_rag_ingestion(background_tasks: BackgroundTasks):
    """
    Spawns the local RAG ingestion worker thread to extract text from all /RAG PDFs
    and build the FAISS index.
    """
    background_tasks.add_task(run_ingestion_pipeline)
    logger.info("API: RAG Ingestion triggered in background.")
    return {"status": "INGESTION_STARTED", "message": "PDF text extraction, chunking, and local FAISS indexing started in background thread."}

@router.get("/query")
def semantic_query_rag(
    query: str = Query(..., description="Semantic search query"),
    limit: int = Query(5, description="Number of context records to retrieve")
):
    """
    Performs semantic search query against the local FAISS vector store or keyword fallbacks.
    Returns matched content chunks and detailed citations.
    """
    results = retriever.retrieve_context(query, top_k=limit)
    return {
        "query": query,
        "results_count": len(results),
        "results": results
    }

@router.get("/device-spec/{device_name}")
def lookup_device_specification(device_name: str):
    """
    Classifies the device ID and returns its dynamic, grounded energy specifications
    along with manual citations.
    """
    spec = retriever.retrieve_by_device(device_name)
    return {
        "device": device_name,
        "specification": spec
    }
