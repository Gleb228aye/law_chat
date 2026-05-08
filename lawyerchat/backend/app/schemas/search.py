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
    chunk_index: int
    content: str
    article_number: str | None = None
    article_title: str | None = None
    distance: float
    similarity: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total_results: int
    note: str
