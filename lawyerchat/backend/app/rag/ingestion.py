import json
from json import JSONDecodeError
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models.chunk import Chunk
from app.models.document import Document
from app.rag.embedder import Embedder
from app.rag.references import extract_referenced_articles
from app.rag.splitter import split_legal_text


def default_docs_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "legal_docs"


def _clean_optional_string(value: object) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _clean_referenced_articles(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            result.append(text)
    return result


def _load_txt_chunks(file_path: Path) -> tuple[str, list[dict], list[str]]:
    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        return file_path.stem, [], []

    chunk_items = split_legal_text(
        text,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    return file_path.stem, chunk_items, []


def _load_jsonl_chunks(file_path: Path) -> tuple[str, list[dict], list[str]]:
    chunk_items: list[dict] = []
    issues: list[str] = []
    document_title: str | None = None

    with file_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            raw_line = line.strip()
            if not raw_line:
                continue

            try:
                item = json.loads(raw_line)
            except JSONDecodeError as exc:
                issues.append(
                    f"{file_path.name}: line {line_number} skipped, invalid JSON "
                    f"({exc.msg})"
                )
                continue

            if not isinstance(item, dict):
                issues.append(
                    f"{file_path.name}: line {line_number} skipped, "
                    "JSON value is not an object"
                )
                continue

            document_title = document_title or _clean_optional_string(
                item.get("document_title")
            )
            content = _clean_optional_string(item.get("text"))
            if content is None:
                issues.append(
                    f"{file_path.name}: line {line_number} skipped, empty text"
                )
                continue

            chunk_items.append(
                {
                    "content": content,
                    "article_number": _clean_optional_string(
                        item.get("article_number")
                    ),
                    "article_title": _clean_optional_string(item.get("article_title")),
                    "referenced_articles": _clean_referenced_articles(
                        item.get("referenced_articles")
                    ),
                }
            )

    return document_title or file_path.stem, chunk_items, issues


def _load_file_chunks(file_path: Path) -> tuple[str, list[dict], list[str]]:
    if file_path.suffix.lower() == ".jsonl":
        return _load_jsonl_chunks(file_path)
    return _load_txt_chunks(file_path)


def _referenced_articles_for_item(item: dict) -> list[str]:
    if "referenced_articles" in item:
        return item["referenced_articles"]

    return extract_referenced_articles(
        item["content"],
        current_article_number=item.get("article_number"),
    )


def ingest_documents(db: Session, docs_dir: str | Path | None = None) -> dict:
    docs_path = Path(docs_dir) if docs_dir is not None else default_docs_dir()
    docs_path.mkdir(parents=True, exist_ok=True)

    document_files = sorted(
        [*docs_path.glob("*.txt"), *docs_path.glob("*.jsonl")],
        key=lambda path: path.name.lower(),
    )
    if not document_files:
        return {
            "files_found": 0,
            "files_processed": 0,
            "documents_created": 0,
            "chunks_created": 0,
            "skipped_files": [],
            "processed_files": [],
            "message": "No .txt or .jsonl files found in data/legal_docs",
        }

    stats = {
        "files_found": len(document_files),
        "files_processed": 0,
        "documents_created": 0,
        "chunks_created": 0,
        "skipped_files": [],
        "processed_files": [],
        "message": None,
    }
    issues: list[str] = []

    embedder = Embedder()

    try:
        for file_path in document_files:
            document_title, chunk_items, file_issues = _load_file_chunks(file_path)
            issues.extend(file_issues)
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
                title=document_title,
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
                        referenced_articles=_referenced_articles_for_item(item),
                        embedding=embedding,
                    )
                )

            stats["files_processed"] += 1
            stats["documents_created"] += 1
            stats["chunks_created"] += len(chunk_items)
            stats["processed_files"].append(file_path.name)

        if issues:
            stats["message"] = "; ".join(issues)
        else:
            stats["message"] = "Ingestion completed"

        db.commit()
        return stats
    except Exception as exc:
        db.rollback()
        raise RuntimeError(f"Failed to ingest legal documents: {exc}") from exc
