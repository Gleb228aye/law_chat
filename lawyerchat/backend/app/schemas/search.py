from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("query must not be empty")
        return value.strip()


class SearchResult(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    document_title: str | None = None
    chunk_index: int
    content: str
    article_number: str | None = None
    article_title: str | None = None
    section_title: str | None = None
    subsection_title: str | None = None
    chapter_title: str | None = None
    paragraph_title: str | None = None
    source_format: str | None = None
    source_filename: str | None = None
    referenced_articles: list[str] = Field(default_factory=list)
    distance: float
    similarity: float
    semantic_score: float | None = None
    keyword_score: float | None = None
    hybrid_score: float | None = None
    article_boost: float | None = None
    document_boost: float | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total_results: int
    note: str
    retrieval_mode: str | None = None
