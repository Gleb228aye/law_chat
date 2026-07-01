SYSTEM_PROMPT = """
Ты юридический RAG-ассистент для проекта LawyerChat.
Отвечай на русском языке только по предоставленному контексту из загруженных документов.
Не используй сведения вне контекста и не додумывай отсутствующие нормы.
Если в контексте нет ответа, скажи: "В загруженных документах недостаточно информации для ответа."
Не называй ответ юридической консультацией.
Формулируй ответ понятным языком.
Не перечисляй технические источники, названия файлов, chunk_index или служебные идентификаторы.
Источники будут показаны отдельно интерфейсом.
""".strip()


def _format_referenced_articles(referenced_articles: list[str] | None) -> str:
    if not referenced_articles:
        return "нет"
    return ", ".join(referenced_articles)


def _format_optional_source_line(label: str, value: str | None) -> str | None:
    if not value:
        return None
    return f"{label}: {value}"


def build_rag_prompt(query: str, chunks: list[dict]) -> str:
    context_blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        article_number = chunk.get("article_number") or "не указана"
        article_title = chunk.get("article_title") or "не указано"
        referenced_articles = _format_referenced_articles(
            chunk.get("referenced_articles") or []
        )
        source_lines = [
            f"[Источник {index}]",
            _format_optional_source_line("Документ", chunk.get("document_title")),
            _format_optional_source_line("Раздел", chunk.get("section_title")),
            _format_optional_source_line("Подраздел", chunk.get("subsection_title")),
            _format_optional_source_line("Глава", chunk.get("chapter_title")),
            _format_optional_source_line("Параграф", chunk.get("paragraph_title")),
            f"Статья: {article_number}",
            f"Название статьи: {article_title}",
            f"Ссылки на статьи: {referenced_articles}",
            "Текст:",
            chunk.get("content") or "",
        ]
        context_blocks.append(
            "\n".join(line for line in source_lines if line is not None)
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
            "- Не добавляй технический список источников в текст ответа.",
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
            "document_title": chunk.get("document_title"),
            "filename": chunk.get("filename"),
            "article_number": chunk.get("article_number"),
            "article_title": chunk.get("article_title"),
            "section_title": chunk.get("section_title"),
            "subsection_title": chunk.get("subsection_title"),
            "chapter_title": chunk.get("chapter_title"),
            "paragraph_title": chunk.get("paragraph_title"),
            "source_format": chunk.get("source_format"),
            "source_filename": chunk.get("source_filename"),
            "chunk_index": chunk.get("chunk_index"),
            "referenced_articles": chunk.get("referenced_articles") or [],
        }
        for chunk in chunks
    ]
