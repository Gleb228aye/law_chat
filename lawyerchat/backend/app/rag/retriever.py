from sqlalchemy import text
from sqlalchemy.orm import Session

from app.rag.embedder import Embedder


class Retriever:
    def __init__(self, db: Session, embedder: Embedder):
        self.db = db
        self.embedder = embedder

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not query or not query.strip():
            raise ValueError("Search query must not be empty")

        query_embedding = self.embedder.embed_text(query.strip())
        query_vector = "[" + ",".join(str(value) for value in query_embedding) + "]"

        sql = text(
            """
            SELECT
                chunks.id AS chunk_id,
                chunks.document_id AS document_id,
                documents.filename AS filename,
                chunks.chunk_index AS chunk_index,
                chunks.content AS content,
                chunks.embedding <=> CAST(:query_embedding AS vector) AS distance
            FROM chunks
            JOIN documents ON documents.id = chunks.document_id
            ORDER BY chunks.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :top_k
            """
        )
        rows = self.db.execute(
            sql,
            {"query_embedding": query_vector, "top_k": top_k},
        ).mappings()

        return [
            {
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "filename": row["filename"],
                "chunk_index": row["chunk_index"],
                "content": row["content"],
                "distance": float(row["distance"]),
            }
            for row in rows
        ]
