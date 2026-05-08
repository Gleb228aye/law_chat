from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models.chunk import Chunk
from app.models.document import Document
from app.rag.embedder import Embedder
from app.rag.splitter import split_legal_text


def default_docs_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "legal_docs"


def ingest_documents(db: Session, docs_dir: str | Path | None = None) -> dict:
    docs_path = Path(docs_dir) if docs_dir is not None else default_docs_dir()
    docs_path.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(docs_path.glob("*.txt"))
    if not txt_files:
        return {
            "files_found": 0,
            "files_processed": 0,
            "documents_created": 0,
            "chunks_created": 0,
            "skipped_files": [],
            "processed_files": [],
            "message": "No .txt files found in data/legal_docs",
        }

    stats = {
        "files_found": len(txt_files),
        "files_processed": 0,
        "documents_created": 0,
        "chunks_created": 0,
        "skipped_files": [],
        "processed_files": [],
        "message": None,
    }

    embedder = Embedder()

    try:
        for file_path in txt_files:
            text = file_path.read_text(encoding="utf-8").strip()
            if not text:
                stats["skipped_files"].append(file_path.name)
                continue

            chunk_items = split_legal_text(
                text,
                chunk_size=settings.chunk_size,
            )
            if not chunk_items:
                stats["skipped_files"].append(file_path.name)
                continue

            existing_document = (
                db.query(Document).filter(Document.filename == file_path.name).first()
            )
            if existing_document is not None:
                db.delete(existing_document)
                db.flush()

            document = Document(
                filename=file_path.name,
                title=file_path.stem,
                source_path=str(file_path),
            )
            db.add(document)
            db.flush()

            texts = [item["content"] for item in chunk_items]
            embeddings = embedder.embed_texts(texts)
            for index, (item, embedding) in enumerate(zip(chunk_items, embeddings)):
                db.add(
                    Chunk(
                        document_id=document.id,
                        chunk_index=index,
                        content=item["content"],
                        article_number=item.get("article_number"),
                        article_title=item.get("article_title"),
                        embedding=embedding,
                    )
                )

            stats["files_processed"] += 1
            stats["documents_created"] += 1
            stats["chunks_created"] += len(chunk_items)
            stats["processed_files"].append(file_path.name)

        db.commit()
        return stats
    except Exception as exc:
        db.rollback()
        raise RuntimeError(f"Failed to ingest legal documents: {exc}") from exc
