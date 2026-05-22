import csv
import os
import re
from pathlib import Path
from statistics import mean, median

from app.rag.splitter import split_legal_text


ARTICLE_REFERENCE_PATTERN = re.compile(r"Статья\s+([0-9]+(?:\.[0-9]+)*)")
CSV_FIELDS = (
    "chunk_index",
    "article_number",
    "article_title",
    "length",
    "start_text",
    "content",
)


def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_env_file_value(env_path: Path, setting_name: str) -> str | None:
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        name, value = stripped.split("=", maxsplit=1)
        if name.strip() == setting_name:
            return value.strip().strip("\"'")
    return None


def _read_int_setting(
    backend_dir: Path,
    setting_name: str,
    default_value: int,
) -> int:
    raw_value = os.getenv(setting_name)
    if raw_value is None:
        raw_value = _read_env_file_value(backend_dir / ".env", setting_name)
    if raw_value is None:
        return default_value

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{setting_name} must be an integer") from exc


def _preview(text: str, max_length: int = 200) -> str:
    return " ".join(text.split())[:max_length]


def _has_suspicious_article_number(chunk: dict) -> bool:
    article_in_text = ARTICLE_REFERENCE_PATTERN.search(chunk["content"])
    return bool(
        article_in_text
        and chunk.get("article_number") != article_in_text.group(1)
    )


def _write_csv(report_path: Path, chunks: list[dict]) -> None:
    with report_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for chunk_index, chunk in enumerate(chunks):
            content = chunk["content"]
            writer.writerow(
                {
                    "chunk_index": chunk_index,
                    "article_number": chunk.get("article_number") or "",
                    "article_title": chunk.get("article_title") or "",
                    "length": len(content),
                    "start_text": _preview(content),
                    "content": content,
                }
            )


def _print_stats(file_path: Path, chunks: list[dict], report_path: Path) -> None:
    lengths = [len(chunk["content"]) for chunk in chunks]
    with_article = sum(bool(chunk.get("article_number")) for chunk in chunks)
    page_breaks = sum("\f" in chunk["content"] for chunk in chunks)
    suspicious = sum(_has_suspicious_article_number(chunk) for chunk in chunks)

    print(f"File: {file_path.name}")
    print(f"  chunks: {len(chunks)}")
    print(f"  chunks_with_article_number: {with_article}")
    print(f"  chunks_without_article_number: {len(chunks) - with_article}")
    if lengths:
        print(
            "  length_min_avg_median_max: "
            f"{min(lengths)} / {mean(lengths):.1f} / "
            f"{median(lengths):.1f} / {max(lengths)}"
        )
    else:
        print("  length_min_avg_median_max: 0 / 0 / 0 / 0")
    print(f"  chunks_with_form_feed: {page_breaks}")
    print(f"  potentially_wrong_article_number: {suspicious}")
    print(f"  csv_report: {report_path}")


def main() -> None:
    backend_dir = _backend_dir()
    chunk_size = _read_int_setting(backend_dir, "CHUNK_SIZE", 1200)
    chunk_overlap = _read_int_setting(backend_dir, "CHUNK_OVERLAP", 200)
    docs_dir = backend_dir / "data" / "legal_docs"
    reports_dir = backend_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(docs_dir.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {docs_dir}")
        return

    for file_path in txt_files:
        text = file_path.read_text(encoding="utf-8")
        chunks = split_legal_text(
            text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        report_path = reports_dir / f"{file_path.stem}_chunks.csv"
        _write_csv(report_path, chunks)
        _print_stats(file_path, chunks, report_path)


if __name__ == "__main__":
    main()
