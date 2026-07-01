import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from docx import Document as DocxDocument

from app.rag.references import extract_referenced_articles


SECTION_PATTERN = re.compile(r"^Раздел\s+.+", re.IGNORECASE)
SUBSECTION_PATTERN = re.compile(r"^Подраздел\s+.+", re.IGNORECASE)
CHAPTER_PATTERN = re.compile(r"^Глава\s+.+", re.IGNORECASE)
PARAGRAPH_PATTERN = re.compile(r"^(?:Параграф|§)\s+.+", re.IGNORECASE)
ARTICLE_PATTERN = re.compile(
    r"^Статья\s+(?P<number>\d+(?:\.\d+)*)(?:[.\s]+(?P<title>.*))?$",
    re.IGNORECASE,
)
SPACE_PATTERN = re.compile(r"\s+")

KNOWN_DOCUMENTS = {
    "zkpp_rf": {
        "document_title": "Закон Российской Федерации «О защите прав потребителей»",
        "output_filename": "zakon_o_zashite_prav_potrebiteley.jsonl",
        "keywords": ("защит", "прав", "потребител"),
    },
    "sk_rf": {
        "document_title": "Семейный кодекс Российской Федерации",
        "output_filename": "semeynyy_kodeks_rf.jsonl",
        "keywords": ("семейн", "кодекс"),
    },
    "zhk_rf": {
        "document_title": "Жилищный кодекс Российской Федерации",
        "output_filename": "zhilishchnyy_kodeks_rf.jsonl",
        "keywords": ("жилищн", "кодекс"),
    },
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


def _normalize_line(value: str) -> str:
    value = value.replace("\ufeff", "")
    value = SPACE_PATTERN.sub(" ", value)
    return value.strip()


def read_docx_lines(input_path: Path) -> list[str]:
    try:
        document = DocxDocument(str(input_path))
    except Exception as exc:
        raise ConversionError(f"Cannot read DOCX file {input_path}: {exc}") from exc

    lines: list[str] = []
    for paragraph in document.paragraphs:
        line = _normalize_line(paragraph.text)
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


def convert_lines_to_records(
    lines: list[str],
    *,
    source_filename: str,
    document_id: str,
    document_title: str,
) -> list[dict[str, Any]]:
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
        if SECTION_PATTERN.match(line):
            flush_article()
            context["section_title"] = line
            context["subsection_title"] = None
            context["chapter_title"] = None
            context["paragraph_title"] = None
            continue

        if SUBSECTION_PATTERN.match(line):
            flush_article()
            context["subsection_title"] = line
            context["chapter_title"] = None
            context["paragraph_title"] = None
            continue

        if CHAPTER_PATTERN.match(line):
            flush_article()
            context["chapter_title"] = line
            context["paragraph_title"] = None
            continue

        if PARAGRAPH_PATTERN.match(line):
            flush_article()
            context["paragraph_title"] = line
            continue

        article_match = ARTICLE_PATTERN.match(line)
        if article_match:
            flush_article()
            current_article = {
                "document_id": document_id,
                "document_title": document_title,
                "source_format": "docx",
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


def convert_docx_to_records(
    input_path: Path,
    *,
    document_id: str,
    document_title: str,
) -> list[dict[str, Any]]:
    return convert_lines_to_records(
        read_docx_lines(input_path),
        source_filename=input_path.name,
        document_id=document_id,
        document_title=document_title,
    )


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
    records = convert_docx_to_records(
        input_path,
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


def infer_document_metadata(file_path: Path) -> tuple[str, str, str, bool]:
    normalized = _normalize_filename(file_path.stem)
    for document_id, metadata in KNOWN_DOCUMENTS.items():
        if all(keyword in normalized for keyword in metadata["keywords"]):
            return (
                document_id,
                metadata["document_title"],
                metadata["output_filename"],
                True,
            )

    safe_name = _slugify(file_path.stem)
    return safe_name, file_path.stem, f"{safe_name}.jsonl", False


def _docx_files(input_dir: Path) -> list[Path]:
    if not input_dir.is_dir():
        raise ConversionError(f"Input directory does not exist: {input_dir}")

    return sorted(
        (
            path
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".docx"
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

    input_path = Path(args.input)
    if input_path.suffix.lower() != ".docx":
        raise ConversionError(f"Input file must have .docx extension: {input_path}")

    count = convert_file(
        input_path,
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
    files = _docx_files(input_dir)
    if not files:
        raise ConversionError(f"No .docx files found in {input_dir}")

    converted = 0
    total_records = 0
    failures: list[str] = []

    for input_path in files:
        document_id, document_title, output_filename, recognized = (
            infer_document_metadata(input_path)
        )
        if not recognized:
            print(
                f"WARNING: unknown document {input_path.name}; "
                f"using document_id={document_id}",
                file=sys.stderr,
            )

        output_path = output_dir / output_filename
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
        description="Convert ConsultantPlus DOCX legal documents to JSONL."
    )
    parser.add_argument("--input", help="Path to one .docx file")
    parser.add_argument("--output", help="Output .jsonl path for single conversion")
    parser.add_argument("--document-id", help="Document id for single conversion")
    parser.add_argument("--document-title", help="Document title for single conversion")
    parser.add_argument("--input-dir", help="Directory with .docx files")
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
