import re

ARTICLE_PATTERN = re.compile(
    r"^[ \t]*Статья[ \t]+(?P<number>\d+(?:\.\d+)*)(?:\.[ \t]*(?P<title>[^\n]*))?$",
    re.IGNORECASE | re.MULTILINE,
)


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_long_paragraph(paragraph: str, chunk_size: int) -> list[str]:
    parts: list[str] = []
    start = 0
    paragraph = paragraph.strip()

    while start < len(paragraph):
        end = min(start + chunk_size, len(paragraph))
        if end < len(paragraph):
            sentence_end = max(
                paragraph.rfind(".", start, end),
                paragraph.rfind("!", start, end),
                paragraph.rfind("?", start, end),
                paragraph.rfind(";", start, end),
            )
            if sentence_end > start + chunk_size // 2:
                end = sentence_end + 1
            else:
                space = paragraph.rfind(" ", start, end)
                if space > start + chunk_size // 2:
                    end = space

        part = paragraph[start:end].strip()
        if part:
            parts.append(part)
        start = end

    return parts


def _apply_overlap(chunks: list[str], chunk_overlap: int) -> list[str]:
    if chunk_overlap <= 0 or len(chunks) <= 1:
        return chunks

    result = [chunks[0]]
    for index in range(1, len(chunks)):
        previous_tail = chunks[index - 1][-chunk_overlap:].strip()
        current = chunks[index].strip()
        if previous_tail and not current.startswith(previous_tail):
            result.append(f"{previous_tail}\n\n{current}".strip())
        else:
            result.append(current)
    return result


def split_text(
    text: str,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be greater than or equal to 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")

    normalized = _normalize_text(text)
    if not normalized:
        return []

    paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
    prepared_parts: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= chunk_size:
            prepared_parts.append(paragraph)
        else:
            prepared_parts.extend(_split_long_paragraph(paragraph, chunk_size))

    chunks: list[str] = []
    current_parts: list[str] = []
    current_length = 0

    for part in prepared_parts:
        separator_length = 2 if current_parts else 0
        next_length = current_length + separator_length + len(part)

        if current_parts and next_length > chunk_size:
            chunks.append("\n\n".join(current_parts).strip())
            current_parts = [part]
            current_length = len(part)
        else:
            current_parts.append(part)
            current_length = next_length

    if current_parts:
        chunks.append("\n\n".join(current_parts).strip())

    return [chunk for chunk in _apply_overlap(chunks, chunk_overlap) if chunk.strip()]


def _make_legal_chunk(
    content: str,
    article_number: str | None,
    article_title: str | None,
) -> dict:
    return {
        "content": content,
        "article_number": article_number,
        "article_title": article_title,
    }


def split_legal_text(
    text: str,
    chunk_size: int = 1200,
    chunk_overlap: int = 0,
) -> list[dict]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be greater than or equal to 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")

    normalized = _normalize_text(text)
    if not normalized:
        return []

    article_matches = list(ARTICLE_PATTERN.finditer(normalized))
    if not article_matches:
        return [
            _make_legal_chunk(content=chunk, article_number=None, article_title=None)
            for chunk in split_text(
                normalized,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        ]

    chunks: list[dict] = []
    leading_text = normalized[: article_matches[0].start()].strip()
    if leading_text:
        chunks.extend(
            _make_legal_chunk(content=chunk, article_number=None, article_title=None)
            for chunk in split_text(
                leading_text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )

    for index, match in enumerate(article_matches):
        article_start = match.start()
        article_end = (
            article_matches[index + 1].start()
            if index + 1 < len(article_matches)
            else len(normalized)
        )
        article_text = normalized[article_start:article_end].strip()
        if not article_text:
            continue

        article_number = match.group("number")
        article_title = (match.group("title") or "").strip() or None

        if len(article_text) <= chunk_size:
            chunks.append(
                _make_legal_chunk(
                    content=article_text,
                    article_number=article_number,
                    article_title=article_title,
                )
            )
            continue

        article_parts = split_text(
            article_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        chunks.extend(
            _make_legal_chunk(
                content=part,
                article_number=article_number,
                article_title=article_title,
            )
            for part in article_parts
        )

    return chunks
