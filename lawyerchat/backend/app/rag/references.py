import re


ARTICLE_REFERENCE_PATTERN = re.compile(
    r"\bстать(?:я|и|е|ей|ёй|ю|ях|ями)\b"
    r"(?P<tail>\s+"
    r"\d+(?:\.\d+)*"
    r"(?:\s*(?:,|и|или|либо|и/или|[-–—])\s*\d+(?:\.\d+)*)*"
    r")",
    re.IGNORECASE,
)
ARTICLE_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)*")


def _article_sort_key(article_number: str) -> tuple:
    return tuple(int(part) for part in article_number.split("."))


def extract_referenced_articles(
    text: str,
    current_article_number: str | None = None,
) -> list[str]:
    referenced_articles: set[str] = set()
    for match in ARTICLE_REFERENCE_PATTERN.finditer(text):
        referenced_articles.update(ARTICLE_NUMBER_PATTERN.findall(match.group("tail")))

    if current_article_number:
        referenced_articles.discard(current_article_number)

    return sorted(referenced_articles, key=_article_sort_key)
