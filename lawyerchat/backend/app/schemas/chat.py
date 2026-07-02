from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    retrieval_mode: Literal["semantic", "hybrid"] | None = None

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("query must not be empty")
        return value.strip()


class ChatSource(BaseModel):
    document_title: str | None = None
    filename: str | None = None
    article_number: str | None = None
    article_title: str | None = None
    section_title: str | None = None
    subsection_title: str | None = None
    chapter_title: str | None = None
    paragraph_title: str | None = None
    source_format: str | None = None
    source_filename: str | None = None
    chunk_index: int
    referenced_articles: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    query: str
    answer: str
    sources: list[ChatSource]
    total_sources: int
    retrieval_mode: Literal["semantic", "hybrid"]
