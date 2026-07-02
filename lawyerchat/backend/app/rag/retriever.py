from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.rag.embedder import Embedder


ARTICLE_NUMBER_RE = re.compile(
    r"(?<!\w)ст(?:атья|атье|атьи|атью)?\.?\s*(\d+(?:\.\d+)*)",
    re.IGNORECASE,
)

DOCUMENT_ALIASES: dict[str, tuple[str, ...]] = {
    "tk_rf": (
        "tk_rf",
        "trudovoy_kodeks_rf",
        "trudovoy_kodeks_rossiyskoy_federatsii",
        "трудовой кодекс",
    ),
    "uk_rf": (
        "uk_rf",
        "ugolovnyy_kodeks_rf",
        "ugolovnyy_kodeks_rossiyskoy_federatsii",
        "уголовный кодекс",
    ),
    "gk_rf": (
        "gk_rf",
        "grazhdanskiy_kodeks_rf",
        "grazhdanskiy_kodeks_rossiyskoy_federatsii",
        "гражданский кодекс",
    ),
    "nk_rf": (
        "nk_rf",
        "nalogovyy_kodeks_rf",
        "nalogovyy_kodeks_rossiyskoy_federatsii",
        "налоговый кодекс",
    ),
    "zkpp_rf": (
        "zkpp_rf",
        "zakon_o_zashite_prav_potrebiteley",
        "закон о защите прав потребителей",
        "защите прав потребителей",
    ),
    "sk_rf": (
        "sk_rf",
        "semeynyy_kodeks_rf",
        "semeynyy_kodeks_rossiyskoy_federatsii",
        "семейный кодекс",
    ),
    "zhk_rf": (
        "zhk_rf",
        "zhilishchnyy_kodeks_rf",
        "zhilishchnyy_kodeks_rossiyskoy_federatsii",
        "жилищный кодекс",
    ),
}

LAW_HINT_TERMS: dict[str, tuple[str, ...]] = {
    "tk_rf": (
        "трудовой кодекс",
        "тк рф",
        "работник",
        "работодател",
        "увольнен",
        "зарплат",
    ),
    "uk_rf": (
        "уголовный кодекс",
        "ук рф",
        "преступлен",
        "краж",
        "убийств",
        "мошенничеств",
        "грабеж",
        "грабёж",
    ),
    "gk_rf": (
        "гражданский кодекс",
        "гк рф",
        "договор",
        "сделк",
        "собственност",
        "юридическ",
    ),
    "nk_rf": (
        "налоговый кодекс",
        "нк рф",
        "налог",
        "налогоплательщик",
        "декларац",
    ),
    "zkpp_rf": (
        "закон о защите прав потребителей",
        "зозпп",
        "потребител",
        "покупател",
        "товар ненадлежащего качества",
    ),
    "sk_rf": (
        "семейный кодекс",
        "ск рф",
        "брак",
        "супруг",
        "алимент",
        "родител",
    ),
    "zhk_rf": (
        "жилищный кодекс",
        "жк рф",
        "жилое помещение",
        "многоквартирный дом",
        "собственники помещений",
    ),
}


def extract_article_number(query: str) -> str | None:
    match = ARTICLE_NUMBER_RE.search(query or "")
    return match.group(1) if match else None


def detect_law_hint(query: str) -> str | None:
    normalized_query = re.sub(r"\s+", " ", (query or "").casefold().replace("ё", "е"))
    for law_id, terms in LAW_HINT_TERMS.items():
        if any(term.replace("ё", "е") in normalized_query for term in terms):
            return law_id
    return None


def document_matches_law_hint(document_value: object, law_hint: str | None) -> bool:
    if not document_value or not law_hint or law_hint not in DOCUMENT_ALIASES:
        return False
    normalized_value = re.sub(
        r"[^a-zа-я0-9]+",
        "",
        str(document_value).casefold().replace("ё", "е"),
    )
    return any(
        re.sub(r"[^a-zа-я0-9]+", "", alias.casefold().replace("ё", "е"))
        in normalized_value
        for alias in DOCUMENT_ALIASES[law_hint]
    )


class Retriever:
    def __init__(self, db: Session, embedder: Embedder):
        self.db = db
        self.embedder = embedder

    @staticmethod
    def _validate_query(query: str) -> str:
        if not query or not query.strip():
            raise ValueError("Search query must not be empty")
        return query.strip()

    def _query_vector(self, query: str) -> str:
        query_embedding = self.embedder.embed_text(query)
        return "[" + ",".join(str(value) for value in query_embedding) + "]"

    @staticmethod
    def _serialize_rows(rows) -> list[dict]:
        float_fields = (
            "distance",
            "similarity",
            "semantic_score",
            "keyword_score",
            "article_boost",
            "document_boost",
            "hybrid_score",
        )
        results = []
        for row in rows:
            item = dict(row)
            item["referenced_articles"] = item.get("referenced_articles") or []
            for field in float_fields:
                if item.get(field) is not None:
                    item[field] = float(item[field])
            results.append(item)
        return results

    def search_semantic(self, query: str, top_k: int = 5) -> list[dict]:
        query = self._validate_query(query)
        query_vector = self._query_vector(query)

        sql = text(
            """
            SELECT
                chunks.id AS chunk_id,
                chunks.document_id AS document_id,
                documents.filename AS filename,
                documents.title AS document_title,
                chunks.chunk_index AS chunk_index,
                chunks.content AS content,
                chunks.article_number AS article_number,
                chunks.article_title AS article_title,
                chunks.section_title AS section_title,
                chunks.subsection_title AS subsection_title,
                chunks.chapter_title AS chapter_title,
                chunks.paragraph_title AS paragraph_title,
                chunks.source_format AS source_format,
                chunks.source_filename AS source_filename,
                chunks.referenced_articles AS referenced_articles,
                chunks.embedding <=> CAST(:query_embedding AS vector) AS distance,
                1 - (chunks.embedding <=> CAST(:query_embedding AS vector)) AS similarity,
                1 - (chunks.embedding <=> CAST(:query_embedding AS vector)) AS semantic_score,
                0.0::double precision AS keyword_score,
                0.0::double precision AS article_boost,
                0.0::double precision AS document_boost,
                1 - (chunks.embedding <=> CAST(:query_embedding AS vector)) AS hybrid_score
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
        return self._serialize_rows(rows)

    def search_hybrid(self, query: str, top_k: int = 5) -> list[dict]:
        from app.config import settings

        query = self._validate_query(query)
        query_vector = self._query_vector(query)
        article_number = extract_article_number(query)
        law_hint = detect_law_hint(query)
        law_aliases = list(DOCUMENT_ALIASES.get(law_hint or "", ()))
        candidate_limit = max(top_k * 10, 50)

        sql = text(
            """
            WITH query_data AS (
                SELECT
                    CAST(:query_embedding AS vector) AS embedding,
                    plainto_tsquery('russian', :query_text) AS tsquery
            ),
            semantic_candidates AS (
                SELECT chunks.id
                FROM chunks
                CROSS JOIN query_data
                ORDER BY chunks.embedding <=> query_data.embedding
                LIMIT :candidate_limit
            ),
            keyword_candidates AS (
                SELECT chunks.id
                FROM chunks
                JOIN documents ON documents.id = chunks.document_id
                CROSS JOIN query_data
                WHERE (
                    setweight(to_tsvector('russian', coalesce(documents.title, '')), 'A') ||
                    setweight(to_tsvector('russian', coalesce(chunks.article_title, '')), 'A') ||
                    setweight(to_tsvector('russian', coalesce(chunks.section_title, '')), 'B') ||
                    setweight(to_tsvector('russian', coalesce(chunks.chapter_title, '')), 'B') ||
                    setweight(to_tsvector('russian', coalesce(chunks.content, '')), 'D')
                ) @@ query_data.tsquery
                ORDER BY ts_rank_cd(
                    (
                        setweight(to_tsvector('russian', coalesce(documents.title, '')), 'A') ||
                        setweight(to_tsvector('russian', coalesce(chunks.article_title, '')), 'A') ||
                        setweight(to_tsvector('russian', coalesce(chunks.section_title, '')), 'B') ||
                        setweight(to_tsvector('russian', coalesce(chunks.chapter_title, '')), 'B') ||
                        setweight(to_tsvector('russian', coalesce(chunks.content, '')), 'D')
                    ),
                    query_data.tsquery,
                    32
                ) DESC
                LIMIT :candidate_limit
            ),
            article_candidates AS (
                SELECT chunks.id
                FROM chunks
                WHERE :article_number IS NOT NULL
                  AND chunks.article_number = :article_number
            ),
            candidate_ids AS (
                SELECT id FROM semantic_candidates
                UNION
                SELECT id FROM keyword_candidates
                UNION
                SELECT id FROM article_candidates
            ),
            scores AS (
                SELECT
                    chunks.id AS chunk_id,
                    chunks.document_id,
                    documents.filename,
                    documents.title AS document_title,
                    chunks.chunk_index,
                    chunks.content,
                    chunks.article_number,
                    chunks.article_title,
                    chunks.section_title,
                    chunks.subsection_title,
                    chunks.chapter_title,
                    chunks.paragraph_title,
                    chunks.source_format,
                    chunks.source_filename,
                    chunks.referenced_articles,
                    chunks.embedding <=> query_data.embedding AS distance,
                    1 - (chunks.embedding <=> query_data.embedding) AS semantic_score,
                    ts_rank_cd(
                        (
                            setweight(to_tsvector('russian', coalesce(documents.title, '')), 'A') ||
                            setweight(to_tsvector('russian', coalesce(chunks.article_title, '')), 'A') ||
                            setweight(to_tsvector('russian', coalesce(chunks.section_title, '')), 'B') ||
                            setweight(to_tsvector('russian', coalesce(chunks.chapter_title, '')), 'B') ||
                            setweight(to_tsvector('russian', coalesce(chunks.content, '')), 'D')
                        ),
                        query_data.tsquery,
                        32
                    ) AS keyword_score,
                    CASE
                        WHEN :article_number IS NOT NULL
                             AND chunks.article_number = :article_number THEN 0.65
                        ELSE 0.0
                    END AS article_boost,
                    CASE
                        WHEN :law_hint IS NOT NULL
                             AND EXISTS (
                                 SELECT 1
                                 FROM unnest(CAST(:law_aliases AS text[])) AS alias(value)
                                 WHERE lower(
                                     concat_ws(
                                         ' ',
                                         documents.filename,
                                         documents.title,
                                         chunks.source_filename
                                     )
                                 ) LIKE '%' || lower(alias.value) || '%'
                             ) THEN 0.35
                        ELSE 0.0
                    END AS document_boost
                FROM candidate_ids
                JOIN chunks ON chunks.id = candidate_ids.id
                JOIN documents ON documents.id = chunks.document_id
                CROSS JOIN query_data
            )
            SELECT
                scores.*,
                scores.semantic_score AS similarity,
                (
                    :semantic_weight * scores.semantic_score +
                    :keyword_weight * scores.keyword_score +
                    :metadata_weight * LEAST(
                        1.0,
                        scores.article_boost + scores.document_boost
                    )
                ) AS hybrid_score
            FROM scores
            ORDER BY hybrid_score DESC
            LIMIT :top_k
            """
        )
        rows = self.db.execute(
            sql,
            {
                "query_embedding": query_vector,
                "query_text": query,
                "article_number": article_number,
                "law_hint": law_hint,
                "law_aliases": law_aliases,
                "semantic_weight": settings.hybrid_semantic_weight,
                "keyword_weight": settings.hybrid_keyword_weight,
                "metadata_weight": settings.hybrid_metadata_weight,
                "candidate_limit": candidate_limit,
                "top_k": top_k,
            },
        ).mappings()
        return self._serialize_rows(rows)

    def search(
        self,
        query: str,
        top_k: int = 5,
        retrieval_mode: str | None = None,
    ) -> list[dict]:
        from app.config import settings

        mode = (retrieval_mode or settings.retrieval_mode).casefold()
        if mode == "semantic":
            return self.search_semantic(query, top_k)
        if mode == "hybrid":
            return self.search_hybrid(query, top_k)
        raise ValueError(f"Unsupported retrieval mode: {mode}")
