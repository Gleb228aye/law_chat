from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models.chunk import Chunk
from app.rag.embedder import Embedder
from app.rag.retriever import Retriever
from app.schemas.search import SearchRequest, SearchResponse


router = APIRouter()

RETRIEVAL_NOTE = (
    "Это результаты поиска по загруженным документам. "
    "Они не являются юридической консультацией."
)


@router.post("/search", response_model=SearchResponse)
def search_documents(request: SearchRequest, db: Session = Depends(get_db)):
    effective_mode = (request.retrieval_mode or settings.retrieval_mode).casefold()
    chunks_count = db.query(Chunk.id).limit(1).count()
    if chunks_count == 0:
        return SearchResponse(
            query=request.query,
            results=[],
            total_results=0,
            retrieval_mode=effective_mode,
            note=(
                "В базе пока нет проиндексированных фрагментов. "
                "Добавьте .jsonl документы в backend/data/legal_docs "
                "или конвертируйте HTML из backend/data/raw_html, затем запустите индексацию. "
                + RETRIEVAL_NOTE
            ),
        )

    embedder = Embedder()
    retriever = Retriever(db=db, embedder=embedder)
    results = retriever.search(
        query=request.query,
        top_k=request.top_k,
        retrieval_mode=effective_mode,
    )

    return SearchResponse(
        query=request.query,
        results=results,
        total_results=len(results),
        note=RETRIEVAL_NOTE,
        retrieval_mode=effective_mode,
    )
