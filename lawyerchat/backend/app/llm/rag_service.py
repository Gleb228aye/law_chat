from sqlalchemy.orm import Session

from app.config import settings
from app.llm.client import LLMClient, LLMConfigurationError
from app.llm.prompt_builder import SYSTEM_PROMPT, build_rag_prompt, build_sources
from app.rag.embedder import Embedder
from app.rag.retriever import Retriever


class RAGChatService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def answer(
        self,
        query: str,
        top_k: int,
        retrieval_mode: str | None = None,
    ) -> dict:
        if not settings.llm_api_key:
            raise LLMConfigurationError("LLM is not configured")

        embedder = Embedder()
        retriever = Retriever(db=self.db, embedder=embedder)
        effective_mode = (retrieval_mode or settings.retrieval_mode).casefold()
        chunks = retriever.search(
            query=query,
            top_k=top_k,
            retrieval_mode=effective_mode,
        )

        prompt = build_rag_prompt(query=query, chunks=chunks)
        answer = LLMClient().generate_answer(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
        )

        return {
            "answer": answer,
            "sources": build_sources(chunks),
            "total_sources": len(chunks),
            "retrieval_mode": effective_mode,
        }
