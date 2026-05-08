from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents, search
from app.db import check_database_connection, check_pgvector_extension, create_tables


app = FastAPI(title="LawyerChat Retrieval API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(documents.router, prefix="/api", tags=["documents"])


@app.on_event("startup")
def on_startup() -> None:
    create_tables()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "database": check_database_connection(),
        "pgvector": check_pgvector_extension(),
    }
