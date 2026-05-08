from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.chunk import Chunk
from app.models.document import Document
from app.rag.ingestion import ingest_documents
from app.schemas.documents import ChunkItem, DocumentItem, IngestResponse


router = APIRouter()


@router.get("/documents", response_model=list[DocumentItem])
def list_documents(db: Session = Depends(get_db)):
    rows = (
        db.query(Document, func.count(Chunk.id).label("chunks_count"))
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
        .all()
    )

    return [
        DocumentItem(
            id=document.id,
            filename=document.filename,
            title=document.title,
            source_path=document.source_path,
            chunks_count=chunks_count,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        for document, chunks_count in rows
    ]


@router.get("/documents/{document_id}/chunks", response_model=list[ChunkItem])
def list_document_chunks(document_id: int, db: Session = Depends(get_db)):
    document_exists = db.query(Document.id).filter(Document.id == document_id).first()
    if document_exists is None:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index.asc())
        .all()
    )
    return chunks


@router.post("/documents/reindex", response_model=IngestResponse)
def reindex_documents(db: Session = Depends(get_db)):
    return ingest_documents(db)
