SYSTEM_PROMPT = """
Ты юридический RAG-ассистент для проекта LawyerChat.
Отвечай на русском языке только по предоставленному контексту из загруженных документов.
Не используй сведения вне контекста и не додумывай отсутствующие нормы.
Если в контексте нет ответа, скажи: "В загруженных документах недостаточно информации для ответа."
Не называй ответ юридической консультацией.
В конце ответа перечисли источники: файл, статья, название статьи, chunk_index.
""".strip()


def _format_referenced_articles(referenced_articles: list[str] | None) -> str:
    if not referenced_articles:
        return "нет"
    return ", ".join(referenced_articles)


def build_rag_prompt(query: str, chunks: list[dict]) -> str:
    context_blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        article_number = chunk.get("article_number") or "не указана"
        article_title = chunk.get("article_title") or "не указано"
        referenced_articles = _format_referenced_articles(
            chunk.get("referenced_articles") or []
        )
        context_blocks.append(
            "\n".join(
                [
                    f"[Источник {index}]",
                    f"Файл: {chunk.get('filename') or 'не указан'}",
                    f"Статья: {article_number}",
                    f"Название статьи: {article_title}",
                    f"chunk_index: {chunk.get('chunk_index')}",
                    f"Ссылки на статьи: {referenced_articles}",
                    "Текст:",
                    chunk.get("content") or "",
                ]
            )
        )

    context = "\n\n---\n\n".join(context_blocks) or "Контекст не найден."
    return "\n\n".join(
        [
            "Правила ответа:",
            "- Отвечай только по контексту ниже.",
            "- Не используй сведения вне контекста.",
            "- Если ответа нет в контексте, скажи, что в загруженных документах недостаточно информации.",
            "- Ответ должен быть на русском языке.",
            "- Не называй ответ юридической консультацией.",
            "- Укажи источники: файл, статья, название статьи, chunk_index.",
            "",
            f"Вопрос: {query}",
            "",
            "Контекст:",
            context,
        ]
    )


def build_sources(chunks: list[dict]) -> list[dict]:
    return [
        {
            "filename": chunk.get("filename"),
            "article_number": chunk.get("article_number"),
            "article_title": chunk.get("article_title"),
            "chunk_index": chunk.get("chunk_index"),
            "referenced_articles": chunk.get("referenced_articles") or [],
        }
        for chunk in chunks
    ]
