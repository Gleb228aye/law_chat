import json

from app.db import SessionLocal, create_tables
from app.rag.ingestion import ingest_documents


def main() -> None:
    create_tables()
    db = SessionLocal()
    try:
        result = ingest_documents(db)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
