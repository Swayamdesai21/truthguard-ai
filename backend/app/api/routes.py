"""
FastAPI Routes — TruthGuard AI API Layer

Endpoints:
  GET  /api/health         — Health check
  POST /api/upload         — Upload one or more documents (PDF, DOCX, PPTX, TXT, MD, etc.)
  POST /api/upload-text    — Upload raw text directly
  POST /api/ask            — Run the full fact-checking pipeline
  GET  /api/sessions       — List active sessions
  DELETE /api/sessions/{id} — Clear a session
"""
from __future__ import annotations
import uuid
from typing import Optional, List

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.ingestion_service import ingest_file, ingest_text
from app.services.vector_store import get_session, delete_session, list_sessions
from app.core.graph import run_pipeline

router = APIRouter()


# Supported formats for display
SUPPORTED_FORMATS = [".pdf", ".docx", ".doc", ".pptx", ".ppt", ".txt", ".md", ".csv", ".json", ".xml", ".html"]


# ── Request / Response Models ─────────────────────────────────────────────────

class AskRequest(BaseModel):
    session_id: str
    query: str


class UploadTextRequest(BaseModel):
    session_id: Optional[str] = None
    text: str
    source_name: Optional[str] = "pasted_text"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "TruthGuard AI", "supported_formats": SUPPORTED_FORMATS}


@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(default=None),
):
    """
    Upload one or more documents. Supports PDF, DOCX, PPTX, TXT, MD, CSV, etc.
    If no session_id provided, generates a new one.
    All files are indexed in the same session for cross-document querying.
    """
    if session_id is None or session_id.strip() == "":
        session_id = str(uuid.uuid4())

    results = []
    total_chunks = 0

    for file in files:
        if not file.filename:
            results.append({"filename": "unknown", "chunks": 0, "error": "No filename"})
            continue

        content = await file.read()

        try:
            chunk_count = ingest_file(session_id, content, file.filename)
            results.append({
                "filename": file.filename,
                "chunks": chunk_count,
                "status": "ok" if chunk_count > 0 else "empty",
            })
            total_chunks += chunk_count
        except Exception as e:
            results.append({
                "filename": file.filename,
                "chunks": 0,
                "error": str(e),
            })

    if total_chunks == 0:
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from any uploaded files. "
                   f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )

    return {
        "session_id": session_id,
        "total_chunks": total_chunks,
        "files": results,
        "message": f"Successfully indexed {total_chunks} chunks from {len(results)} file(s).",
    }


@router.post("/upload-text")
async def upload_text(body: UploadTextRequest):
    """Upload plain text directly (no file). Useful for testing."""
    session_id = body.session_id or str(uuid.uuid4())

    if not body.text or len(body.text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Text is too short.")

    chunk_count = ingest_text(session_id, body.text, source_name=body.source_name or "text_input")

    return {
        "session_id": session_id,
        "chunks_created": chunk_count,
        "message": f"Successfully indexed {chunk_count} chunks.",
    }


@router.post("/ask")
async def ask(body: AskRequest):
    """
    Main fact-checking endpoint.
    Runs the full pipeline: RAG → Answer → Claims → Fact-check → Web Verify → Refine.
    """
    if not body.query or len(body.query.strip()) < 3:
        raise HTTPException(status_code=400, detail="Query is too short.")

    session = get_session(body.session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{body.session_id}' not found. Please upload documents first.",
        )

    result = await run_pipeline(body.session_id, body.query)

    if "error" in result and result["error"]:
        raise HTTPException(status_code=422, detail=result["error"])

    return result


@router.get("/sessions")
async def get_sessions():
    """List all active session IDs."""
    return {"sessions": list_sessions()}


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Delete a session and free its memory."""
    delete_session(session_id)
    return {"message": f"Session '{session_id}' cleared."}
