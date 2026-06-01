import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, FeatureNotFound

from app.rag.references import extract_referenced_articles


HTML_SUFFIXES = {".htm", ".html"}

SECTION_PATTERN = re.compile(r"^Раздел\s+.+", re.IGNORECASE)
SUBSECTION_PATTERN = re.compile(r"^Подраздел\s+.+", re.IGNORECASE)
CHAPTER_PATTERN = re.compile(r"^Глава\s+.+", re.IGNORECASE)
PARAGRAPH_PATTERN = re.compile(r"^(?:Параграф|§)\s+.+", re.IGNORECASE)
ARTICLE_PATTERN = re.compile(
    r"^Статья\s+(?P<number>\d+(?:\.\d+)*)(?:[.\s]+(?P<title>.*))?$",
    re.IGNORECASE,
)
SPACE_PATTERN = re.compile(r"[ \t\f\v\u00a0]+")

KNOWN_DOCUMENTS = {
    "tk_rf": "Трудовой кодекс Российской Федерации",
    "uk_rf": "Уголовный кодекс Российской Федерации",
    "nk_rf_part_1": "Налоговый кодекс Российской Федерации. Часть первая",
    "nk_rf_part_2": "Налоговый кодекс Российской Федерации. Часть вторая",
    "gk_rf_part_1": "Гражданский кодекс Российской Федерации. Часть первая",
    "gk_rf_part_2": "Гражданский кодекс Российской Федерации. Часть вторая",
    "gk_rf_part_3": "Гражданский кодекс Российской Федерации. Часть третья",
    "gk_rf_part_4": "Гражданский кодекс Российской Федерации. Часть четвертая",
}

TRANSLITERATION = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)


class ConversionError(RuntimeError):
    pass


def _read_html(file_path: Path) -> str:
    for encoding in ("utf-8", "cp1251"):
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ConversionError(f"Cannot read {file_path} as UTF-8 or cp1251")


def _make_soup(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        return BeautifulSoup(html, "html.parser")


def _normalize_line(line: str) -> str:
    line = line.replace("\ufeff", "")
    line = SPACE_PATTERN.sub(" ", line)
    return line.strip()


def extract_text_lines(html: str) -> list[str]:
    soup = _make_soup(html)
    for tag in soup.find_all(["script", "style", "meta", "noscript"]):
        tag.decompose()

    lines: list[str] = []
    for raw_line in soup.get_text("\n").splitlines():
        line = _normalize_line(raw_line)
        if line:
            lines.append(line)
    return lines


def _clean_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _article_text(lines: list[str]) -> str:
    if len(lines) <= 1:
        return lines[0]
    return f"{lines[0]}\n\n" + "\n".join(lines[1:])


def _is_section(line: str) -> bool:
    return bool(SECTION_PATTERN.match(line))


def _is_subsection(line: str) -> bool:
    return bool(SUBSECTION_PATTERN.match(line))


def _is_chapter(line: str) -> bool:
    return bool(CHAPTER_PATTERN.match(line))


def _is_paragraph(line: str) -> bool:
    return bool(PARAGRAPH_PATTERN.match(line))


def convert_html_to_records(
    html: str,
    *,
    source_filename: str,
    document_id: str,
    document_title: str,
) -> list[dict[str, Any]]:
    lines = extract_text_lines(html)
    records: list[dict[str, Any]] = []
    context: dict[str, str | None] = {
        "section_title": None,
        "subsection_title": None,
        "chapter_title": None,
        "paragraph_title": None,
    }
    current_article: dict[str, Any] | None = None
    current_lines: list[str] = []

    def flush_article() -> None:
        nonlocal current_article, current_lines
        if current_article is None or not current_lines:
            current_article = None
            current_lines = []
            return

        text = _article_text(current_lines)
        records.append(
            {
                **current_article,
                "text": text,
                "referenced_articles": extract_referenced_articles(
                    text,
                    current_article.get("article_number"),
                ),
            }
        )
        current_article = None
        current_lines = []

    for line in lines:
        if _is_section(line):
            flush_article()
            context["section_title"] = line
            context["subsection_title"] = None
            context["chapter_title"] = None
            context["paragraph_title"] = None
            continue

        if _is_subsection(line):
            flush_article()
            context["subsection_title"] = line
            context["chapter_title"] = None
            context["paragraph_title"] = None
            continue

        if _is_chapter(line):
            flush_article()
            context["chapter_title"] = line
            context["paragraph_title"] = None
            continue

        if _is_paragraph(line):
            flush_article()
            context["paragraph_title"] = line
            continue

        article_match = ARTICLE_PATTERN.match(line)
        if article_match:
            flush_article()
            current_article = {
                "document_id": document_id,
                "document_title": document_title,
                "source_format": "html",
                "source_filename": source_filename,
                "section_title": context["section_title"],
                "subsection_title": context["subsection_title"],
                "chapter_title": context["chapter_title"],
                "paragraph_title": context["paragraph_title"],
                "article_number": article_match.group("number"),
                "article_title": _clean_optional_string(article_match.group("title")),
                "source_url": None,
            }
            current_lines = [line]
            continue

        if current_article is not None:
            current_lines.append(line)

    flush_article()
    return records


def write_jsonl(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def convert_file(
    input_path: Path,
    output_path: Path,
    *,
    document_id: str,
    document_title: str,
) -> int:
    html = _read_html(input_path)
    records = convert_html_to_records(
        html,
        source_filename=input_path.name,
        document_id=document_id,
        document_title=document_title,
    )
    if not records:
        raise ConversionError(f"No articles found in {input_path}")

    write_jsonl(records, output_path)
    return len(records)


def _normalize_filename(value: str) -> str:
    return value.casefold().replace("ё", "е")


def _slugify(value: str) -> str:
    value = value.casefold().translate(TRANSLITERATION)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "document"


def infer_document_metadata(file_path: Path) -> tuple[str, str]:
    normalized = _normalize_filename(file_path.stem)

    def title_for(document_id: str) -> str:
        return KNOWN_DOCUMENTS.get(document_id, file_path.stem)

    if any(keyword in normalized for keyword in ("трудов", "tk_rf", "trudov")):
        return "tk_rf", title_for("tk_rf")
    if any(keyword in normalized for keyword in ("уголовн", "uk_rf", "ugolovn")):
        return "uk_rf", title_for("uk_rf")

    is_tax_code = any(keyword in normalized for keyword in ("налогов", "nk_rf", "nalog"))
    if is_tax_code:
        if any(
            keyword in normalized
            for keyword in ("часть вторая", "части второй", "часть 2", "part_2")
        ):
            return "nk_rf_part_2", title_for("nk_rf_part_2")
        return "nk_rf_part_1", title_for("nk_rf_part_1")

    is_civil_code = any(
        keyword in normalized for keyword in ("гражданск", "gk_rf", "grazhd")
    )
    if is_civil_code:
        if any(
            keyword in normalized
            for keyword in ("часть четвертая", "части четвертой", "часть 4", "part_4")
        ):
            return "gk_rf_part_4", title_for("gk_rf_part_4")
        if any(
            keyword in normalized
            for keyword in ("часть третья", "части третьей", "часть 3", "part_3")
        ):
            return "gk_rf_part_3", title_for("gk_rf_part_3")
        if any(
            keyword in normalized
            for keyword in ("часть вторая", "части второй", "часть 2", "part_2")
        ):
            return "gk_rf_part_2", title_for("gk_rf_part_2")
        return "gk_rf_part_1", title_for("gk_rf_part_1")

    return _slugify(file_path.stem), file_path.stem


def _html_files(input_dir: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() in HTML_SUFFIXES
        ),
        key=lambda path: path.name.lower(),
    )


def _convert_single(args: argparse.Namespace) -> int:
    if not args.input or not args.output:
        raise ConversionError("--input and --output are required for single conversion")
    if not args.document_id or not args.document_title:
        raise ConversionError(
            "--document-id and --document-title are required with --input"
        )

    count = convert_file(
        Path(args.input),
        Path(args.output),
        document_id=args.document_id,
        document_title=args.document_title,
    )
    print(f"Converted 1 file, created {count} JSONL records: {args.output}")
    return 0


def _convert_directory(args: argparse.Namespace) -> int:
    if not args.input_dir or not args.output_dir:
        raise ConversionError("--input-dir and --output-dir are required for batch mode")

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    files = _html_files(input_dir)
    if not files:
        raise ConversionError(f"No .htm or .html files found in {input_dir}")

    converted = 0
    total_records = 0
    failures: list[str] = []
    for input_path in files:
        document_id, document_title = infer_document_metadata(input_path)
        output_path = output_dir / f"{document_id}.jsonl"
        try:
            records_count = convert_file(
                input_path,
                output_path,
                document_id=document_id,
                document_title=document_title,
            )
        except ConversionError as exc:
            failures.append(str(exc))
            continue

        converted += 1
        total_records += records_count
        print(f"Converted {input_path.name} -> {output_path} ({records_count} records)")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    print(f"Converted {converted} files, created {total_records} JSONL records")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert ConsultantPlus HTML/HTM legal documents to JSONL."
    )
    parser.add_argument("--input", help="Path to one .htm/.html file")
    parser.add_argument("--output", help="Output .jsonl path for single conversion")
    parser.add_argument("--document-id", help="Document id for single conversion")
    parser.add_argument("--document-title", help="Document title for single conversion")
    parser.add_argument("--input-dir", help="Directory with .htm/.html files")
    parser.add_argument("--output-dir", help="Directory for generated .jsonl files")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.input_dir or args.output_dir:
            return _convert_directory(args)
        return _convert_single(args)
    except ConversionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
