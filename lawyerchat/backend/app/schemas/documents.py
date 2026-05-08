from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    title: str | None
    source_path: str | None
    chunks_count: int
    created_at: datetime
    updated_at: datetime


class ChunkItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    chunk_index: int
    content: str
    created_at: datetime


class IngestResponse(BaseModel):
    files_found: int
    files_processed: int
    documents_created: int
    chunks_created: int
    skipped_files: list[str]
    processed_files: list[str]
    message: str | None
