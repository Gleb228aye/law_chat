import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ARTICLE_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)*")

DOCUMENT_ALIASES = {
    "tk_rf": (
        "tk_rf",
        "trudovoy_kodeks_rf",
        "trudovoj-kodeks-rossijskoj-federatsii",
        "трудовой кодекс российской федерации",
    ),
    "uk_rf": (
        "uk_rf",
        "ugolovnyy_kodeks_rf",
        "уголовный кодекс российской федерации",
    ),
    "gk_rf": (
        "gk_rf",
        "grazhdanskiy_kodeks_rf",
        "гражданский кодекс российской федерации",
        "гражданский кодекс российской федерации часть первая",
        "гражданский кодекс российской федерации часть вторая",
    ),
    "nk_rf": (
        "nk_rf",
        "nalogovyy_kodeks_rf",
        "налоговый кодекс российской федерации",
        "налоговый кодекс российской федерации часть первая",
        "налоговый кодекс российской федерации часть вторая",
    ),
    "sk_rf": (
        "sk_rf",
        "semeynyy_kodeks_rf",
        "семейный кодекс российской федерации",
    ),
    "zhk_rf": (
        "zhk_rf",
        "zhilishchnyy_kodeks_rf",
        "жилищный кодекс российской федерации",
    ),
}


def normalize_article_number(value: object) -> str | None:
    if value is None:
        return None

    match = ARTICLE_NUMBER_PATTERN.search(str(value))
    return match.group(0) if match else None


def normalize_document_identity(value: object) -> str:
    if value is None:
        return ""
    text = str(value).casefold().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", "", text)


def _alias_key(value: object) -> str | None:
    normalized_value = normalize_document_identity(value)
    if not normalized_value:
        return None

    for document_id, aliases in DOCUMENT_ALIASES.items():
        normalized_id = normalize_document_identity(document_id)
        normalized_aliases = {
            normalize_document_identity(alias)
            for alias in aliases
        }
        if (
            normalized_value == normalized_id
            or normalized_value.startswith(normalized_id)
            or any(
                normalized_value == alias
                or alias in normalized_value
                or normalized_value in alias
                for alias in normalized_aliases
            )
        ):
            return document_id
    return None


def _expected_document_aliases(case: dict[str, Any]) -> set[str]:
    expected_id = case.get("expected_document_id")
    expected_title = case.get("expected_document_title")
    alias_key = _alias_key(expected_id) if expected_id else _alias_key(expected_title)

    if alias_key:
        return {
            normalize_document_identity(alias)
            for alias in DOCUMENT_ALIASES[alias_key]
        }

    fallback_value = expected_id or expected_title
    normalized_fallback = normalize_document_identity(fallback_value)
    return {normalized_fallback} if normalized_fallback else set()


def _document_matches(case: dict[str, Any], result: dict[str, Any]) -> bool:
    expected_aliases = _expected_document_aliases(case)
    if not expected_aliases:
        return True

    result_values = (
        result.get("document_title"),
        result.get("filename"),
        result.get("source_filename"),
        result.get("document_id"),
    )
    normalized_results: set[str] = set()
    for value in result_values:
        normalized_value = normalize_document_identity(value)
        if normalized_value:
            normalized_results.add(normalized_value)

    return any(
        alias in result_value or result_value in alias
        for alias in expected_aliases
        for result_value in normalized_results
    )


def is_expected_match(case: dict[str, Any], result: dict[str, Any]) -> bool:
    expected_articles = {
        article
        for article in (
            normalize_article_number(value)
            for value in case.get("expected_article_numbers", [])
        )
        if article
    }
    result_article = normalize_article_number(result.get("article_number"))

    return (
        bool(result_article)
        and result_article in expected_articles
        and _document_matches(case, result)
    )


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def evaluate_case_results(
    case: dict[str, Any],
    results: list[dict[str, Any]],
    top_k: int = 20,
) -> dict[str, Any]:
    rank: int | None = None
    matched_result: dict[str, Any] | None = None

    for index, result in enumerate(results, start=1):
        if is_expected_match(case, result):
            rank = index
            matched_result = result
            break

    first_result = results[0] if results else {}

    def hit_at(depth: int) -> bool | None:
        if top_k < depth:
            return None
        return rank is not None and rank <= depth

    return {
        "case": case,
        "top_results": results,
        "matched_result": matched_result,
        "hit_top_1": hit_at(1),
        "hit_top_3": hit_at(3),
        "hit_top_5": hit_at(5),
        "hit_top_10": hit_at(10),
        "hit_top_20": hit_at(20),
        "rank": rank,
        "reciprocal_rank": 1.0 / rank if rank else 0.0,
        "best_similarity": _optional_float(first_result.get("similarity")),
        "best_distance": _optional_float(first_result.get("distance")),
        "semantic_score": _optional_float(first_result.get("semantic_score")),
        "keyword_score": _optional_float(first_result.get("keyword_score")),
        "hybrid_score": _optional_float(first_result.get("hybrid_score")),
    }


def calculate_summary_metrics(
    evaluations: list[dict[str, Any]],
) -> dict[str, Any]:
    count = len(evaluations)
    similarities = [
        item["best_similarity"]
        for item in evaluations
        if item.get("best_similarity") is not None
    ]

    metrics: dict[str, Any] = {
        "questions_count": count,
        "mrr": (
            sum(item["reciprocal_rank"] for item in evaluations) / count
            if count
            else 0.0
        ),
        "average_first_similarity": (
            sum(similarities) / len(similarities) if similarities else 0.0
        ),
    }
    for depth in (1, 3, 5, 10, 20):
        values = [
            item[f"hit_top_{depth}"]
            for item in evaluations
            if item.get(f"hit_top_{depth}") is not None
        ]
        metrics[f"hit_top_{depth}_count"] = (
            sum(bool(value) for value in values) if values else None
        )
        metrics[f"top_{depth}_accuracy"] = (
            sum(bool(value) for value in values) / len(values)
            if values
            else None
        )
    return metrics


def calculate_grouped_metrics(
    evaluations: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for evaluation in evaluations:
        grouped[evaluation["case"].get("law") or "Без названия"].append(evaluation)

    return {
        law: calculate_summary_metrics(items)
        for law, items in sorted(grouped.items())
    }


def load_cases(cases_path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(cases_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot load evaluation cases from {cases_path}: {exc}") from exc

    if not isinstance(data, list) or not data:
        raise RuntimeError("Evaluation cases must be a non-empty JSON array")

    seen_ids: set[str] = set()
    for index, case in enumerate(data, start=1):
        if not isinstance(case, dict):
            raise RuntimeError(f"Evaluation case #{index} must be an object")
        case_id = str(case.get("id") or "").strip()
        if not case_id:
            raise RuntimeError(f"Evaluation case #{index} has no id")
        if case_id in seen_ids:
            raise RuntimeError(f"Duplicate evaluation case id: {case_id}")
        if not str(case.get("question") or "").strip():
            raise RuntimeError(f"Evaluation case {case_id} has no question")
        if not case.get("expected_article_numbers"):
            raise RuntimeError(f"Evaluation case {case_id} has no expected articles")
        seen_ids.add(case_id)

    return data


def _result_document_name(result: dict[str, Any]) -> str:
    return str(
        result.get("document_title")
        or result.get("filename")
        or result.get("source_filename")
        or result.get("document_id")
        or "Документ не указан"
    )


def _format_similarity(value: object) -> str:
    number = _optional_float(value)
    return f"{number:.4f}" if number is not None else "—"


def _format_top_results(
    results: list[dict[str, Any]],
    limit: int | None = None,
) -> str:
    selected = results[:limit] if limit is not None else results
    lines: list[str] = []
    for index, result in enumerate(selected, start=1):
        article = normalize_article_number(result.get("article_number")) or "—"
        title = result.get("article_title") or "без названия"
        lines.append(
            f"{index}) {_result_document_name(result)}, статья {article}, "
            f"{title}, similarity={_format_similarity(result.get('similarity'))}"
        )
    return " | ".join(lines) if lines else "Результатов нет"


def write_csv_report(
    evaluations: list[dict[str, Any]],
    output_path: Path,
    metadata: dict[str, Any] | None = None,
) -> None:
    metadata = metadata or {}
    fieldnames = [
        "case_id",
        "retrieval_mode",
        "hybrid_semantic_weight",
        "hybrid_keyword_weight",
        "hybrid_metadata_weight",
        "law",
        "question",
        "expected_articles",
        "hit_top_1",
        "hit_top_3",
        "hit_top_5",
        "hit_top_10",
        "hit_top_20",
        "rank",
        "reciprocal_rank",
        "best_similarity",
        "best_distance",
        "semantic_score",
        "keyword_score",
        "hybrid_score",
        "top_results",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for evaluation in evaluations:
            case = evaluation["case"]
            writer.writerow(
                {
                    "case_id": case["id"],
                    "retrieval_mode": metadata.get("retrieval_mode"),
                    "hybrid_semantic_weight": (
                        metadata.get("hybrid_semantic_weight")
                        if metadata.get("retrieval_mode") == "hybrid"
                        else None
                    ),
                    "hybrid_keyword_weight": (
                        metadata.get("hybrid_keyword_weight")
                        if metadata.get("retrieval_mode") == "hybrid"
                        else None
                    ),
                    "hybrid_metadata_weight": (
                        metadata.get("hybrid_metadata_weight")
                        if metadata.get("retrieval_mode") == "hybrid"
                        else None
                    ),
                    "law": case.get("law"),
                    "question": case.get("question"),
                    "expected_articles": ", ".join(
                        str(value)
                        for value in case.get("expected_article_numbers", [])
                    ),
                    "hit_top_1": evaluation["hit_top_1"],
                    "hit_top_3": evaluation["hit_top_3"],
                    "hit_top_5": evaluation["hit_top_5"],
                    "hit_top_10": evaluation["hit_top_10"],
                    "hit_top_20": evaluation["hit_top_20"],
                    "rank": evaluation["rank"],
                    "reciprocal_rank": evaluation["reciprocal_rank"],
                    "best_similarity": evaluation["best_similarity"],
                    "best_distance": evaluation["best_distance"],
                    "semantic_score": evaluation["semantic_score"],
                    "keyword_score": evaluation["keyword_score"],
                    "hybrid_score": evaluation["hybrid_score"],
                    "top_results": _format_top_results(evaluation["top_results"]),
                }
            )


def write_json_report(
    evaluations: list[dict[str, Any]],
    summary: dict[str, Any],
    grouped_metrics: dict[str, dict[str, Any]],
    metadata: dict[str, Any],
    output_path: Path,
) -> None:
    payload = {
        **metadata,
        "summary": summary,
        "metrics_by_law": grouped_metrics,
        "cases": evaluations,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _percent(value: float | None) -> str:
    if value is None:
        return "не рассчитывалось"
    return f"{value * 100:.1f}%"


def _count_text(value: int | None) -> str:
    return str(value) if value is not None else "не рассчитывалось"


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _conclusion_lines(
    summary: dict[str, Any],
    grouped_metrics: dict[str, dict[str, Any]],
    evaluations: list[dict[str, Any]],
) -> list[str]:
    available_depths = [
        depth
        for depth in (1, 3, 5, 10, 20)
        if summary.get(f"top_{depth}_accuracy") is not None
    ]
    deepest_depth = max(available_depths) if available_depths else None
    best_laws: list[str] = []
    if grouped_metrics and deepest_depth is not None:
        best_value = max(
            metrics[f"top_{deepest_depth}_accuracy"]
            for metrics in grouped_metrics.values()
            if metrics[f"top_{deepest_depth}_accuracy"] is not None
        )
        best_laws = [
            law
            for law, metrics in grouped_metrics.items()
            if metrics[f"top_{deepest_depth}_accuracy"] == best_value
        ]

    failed_ids = [
        item["case"]["id"]
        for item in evaluations
        if item["matched_result"] is None
    ]
    lines = [
        f"Проверено вопросов: {summary['questions_count']}.",
        (
            f"Успешно найдено: top-1 — {_count_text(summary['hit_top_1_count'])}, "
            f"top-3 — {_count_text(summary['hit_top_3_count'])}, "
            f"top-5 — {_count_text(summary['hit_top_5_count'])}, "
            f"top-10 — {_count_text(summary['hit_top_10_count'])}, "
            f"top-20 — {_count_text(summary['hit_top_20_count'])}."
        ),
    ]
    if best_laws and deepest_depth is not None:
        lines.append(
            f"Лучший результат top-{deepest_depth}: "
            + ", ".join(best_laws)
            + "."
        )
    if failed_ids:
        lines.append(
            "Требуют проверки корпуса, разбиения или retrieval: "
            + ", ".join(failed_ids)
            + "."
        )
    else:
        lines.append("Все контрольные вопросы найдены в пределах запрошенного top-k.")
    return lines


def build_markdown_report(
    evaluations: list[dict[str, Any]],
    summary: dict[str, Any],
    grouped_metrics: dict[str, dict[str, Any]],
    metadata: dict[str, Any],
) -> str:
    lines = [
        "# Отчёт о тестировании retrieval LawyerChat",
        "",
        f"- Дата и время запуска: {metadata['generated_at']}",
        f"- Количество тестовых вопросов: {summary['questions_count']}",
        f"- top_k: {metadata['top_k']}",
        f"- Retrieval mode: `{metadata['retrieval_mode']}`",
        f"- Модель embeddings: `{metadata['embedding_model']}`",
        f"- База данных доступна: {metadata['database_available']}",
        f"- pgvector доступен: {metadata['pgvector_available']}",
        "",
        "## Итоговые метрики",
        "",
        f"- Top-1 accuracy: {_percent(summary['top_1_accuracy'])}",
        f"- Top-3 accuracy: {_percent(summary['top_3_accuracy'])}",
        f"- Top-5 accuracy: {_percent(summary['top_5_accuracy'])}",
        f"- Top-10 accuracy: {_percent(summary['top_10_accuracy'])}",
        f"- Top-20 accuracy: {_percent(summary['top_20_accuracy'])}",
        f"- MRR: {summary['mrr']:.4f}",
        (
            "- Средняя similarity первого результата: "
            f"{summary['average_first_similarity']:.4f}"
        ),
        "",
        "## Метрики по законам",
        "",
        "| Закон | Количество вопросов | Top-1 | Top-3 | Top-5 | Top-10 | Top-20 | MRR |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    if metadata["retrieval_mode"] == "hybrid":
        lines[7:7] = [
            (
                "- Hybrid weights: "
                f"semantic={metadata['hybrid_semantic_weight']}, "
                f"keyword={metadata['hybrid_keyword_weight']}, "
                f"metadata={metadata['hybrid_metadata_weight']}"
            ),
            "",
        ]

    for law, metrics in grouped_metrics.items():
        lines.append(
            f"| {_markdown_cell(law)} | {metrics['questions_count']} | "
            f"{_percent(metrics['top_1_accuracy'])} | "
            f"{_percent(metrics['top_3_accuracy'])} | "
            f"{_percent(metrics['top_5_accuracy'])} | "
            f"{_percent(metrics['top_10_accuracy'])} | "
            f"{_percent(metrics['top_20_accuracy'])} | {metrics['mrr']:.4f} |"
        )

    lines.extend(["", "## Ошибочные случаи", ""])
    failed = [item for item in evaluations if item["matched_result"] is None]
    if not failed:
        lines.append("Ошибочных случаев в пределах запрошенного top-k нет.")
    else:
        for evaluation in failed:
            case = evaluation["case"]
            lines.extend(
                [
                    f"### {case['id']}",
                    "",
                    f"- Вопрос: {case['question']}",
                    (
                        "- Ожидаемые статьи: "
                        + ", ".join(case.get("expected_article_numbers", []))
                    ),
                    f"- Найденные результаты: {_format_top_results(evaluation['top_results'])}",
                    f"- Комментарий: {case.get('comment') or '—'}",
                    "",
                ]
            )

    lines.extend(
        [
            "## Подробные результаты",
            "",
            "| id | Закон | Вопрос | Ожидаемые статьи | Позиция | top-10 найденных статей | Результат |",
            "|---|---|---|---|---:|---|---|",
        ]
    )
    for evaluation in evaluations:
        case = evaluation["case"]
        top_articles = ", ".join(
            normalize_article_number(result.get("article_number")) or "—"
            for result in evaluation["top_results"][:10]
        )
        lines.append(
            f"| {_markdown_cell(case['id'])} | {_markdown_cell(case.get('law', ''))} | "
            f"{_markdown_cell(case.get('question', ''))} | "
            f"{_markdown_cell(', '.join(case.get('expected_article_numbers', [])))} | "
            f"{evaluation['rank'] or '—'} | {_markdown_cell(top_articles)} | "
            f"{'успех' if evaluation['matched_result'] else 'ошибка'} |"
        )

    lines.extend(["", "## Вывод", ""])
    lines.extend(f"- {line}" for line in _conclusion_lines(
        summary,
        grouped_metrics,
        evaluations,
    ))
    return "\n".join(lines) + "\n"


def write_docx_report(
    evaluations: list[dict[str, Any]],
    summary: dict[str, Any],
    grouped_metrics: dict[str, dict[str, Any]],
    metadata: dict[str, Any],
    output_path: Path,
) -> bool:
    try:
        from docx import Document
    except ImportError:
        print("WARNING: python-docx is not installed; DOCX report skipped", file=sys.stderr)
        return False

    document = Document()
    document.add_heading("Отчёт о тестировании retrieval LawyerChat", level=0)
    document.add_paragraph(f"Дата и время запуска: {metadata['generated_at']}")
    document.add_paragraph(f"Количество вопросов: {summary['questions_count']}")
    document.add_paragraph(f"top_k: {metadata['top_k']}")
    document.add_paragraph(f"Retrieval mode: {metadata['retrieval_mode']}")
    if metadata["retrieval_mode"] == "hybrid":
        document.add_paragraph(
            "Hybrid weights: "
            f"semantic={metadata['hybrid_semantic_weight']}, "
            f"keyword={metadata['hybrid_keyword_weight']}, "
            f"metadata={metadata['hybrid_metadata_weight']}"
        )
    document.add_paragraph(f"Модель embeddings: {metadata['embedding_model']}")
    document.add_paragraph(
        f"База данных: {metadata['database_available']}; "
        f"pgvector: {metadata['pgvector_available']}"
    )

    document.add_heading("Итоговые метрики", level=1)
    summary_table = document.add_table(rows=1, cols=2)
    summary_table.style = "Table Grid"
    summary_table.rows[0].cells[0].text = "Метрика"
    summary_table.rows[0].cells[1].text = "Значение"
    for label, value in (
        ("Top-1 accuracy", _percent(summary["top_1_accuracy"])),
        ("Top-3 accuracy", _percent(summary["top_3_accuracy"])),
        ("Top-5 accuracy", _percent(summary["top_5_accuracy"])),
        ("Top-10 accuracy", _percent(summary["top_10_accuracy"])),
        ("Top-20 accuracy", _percent(summary["top_20_accuracy"])),
        ("MRR", f"{summary['mrr']:.4f}"),
        (
            "Средняя similarity первого результата",
            f"{summary['average_first_similarity']:.4f}",
        ),
    ):
        cells = summary_table.add_row().cells
        cells[0].text = label
        cells[1].text = value

    document.add_heading("Метрики по законам", level=1)
    law_table = document.add_table(rows=1, cols=8)
    law_table.style = "Table Grid"
    for cell, value in zip(
        law_table.rows[0].cells,
        (
            "Закон",
            "Вопросы",
            "Top-1",
            "Top-3",
            "Top-5",
            "Top-10",
            "Top-20",
            "MRR",
        ),
    ):
        cell.text = value
    for law, metrics in grouped_metrics.items():
        cells = law_table.add_row().cells
        values = (
            law,
            str(metrics["questions_count"]),
            _percent(metrics["top_1_accuracy"]),
            _percent(metrics["top_3_accuracy"]),
            _percent(metrics["top_5_accuracy"]),
            _percent(metrics["top_10_accuracy"]),
            _percent(metrics["top_20_accuracy"]),
            f"{metrics['mrr']:.4f}",
        )
        for cell, value in zip(cells, values):
            cell.text = value

    document.add_heading("Ошибочные случаи", level=1)
    failed = [item for item in evaluations if item["matched_result"] is None]
    if not failed:
        document.add_paragraph(
            "Ошибочных случаев в пределах запрошенного top-k нет."
        )
    for evaluation in failed:
        case = evaluation["case"]
        document.add_heading(case["id"], level=2)
        document.add_paragraph(f"Вопрос: {case['question']}")
        document.add_paragraph(
            "Ожидаемые статьи: "
            + ", ".join(case.get("expected_article_numbers", []))
        )
        document.add_paragraph(
            "Найденные результаты: "
            + _format_top_results(evaluation["top_results"])
        )
        document.add_paragraph(f"Комментарий: {case.get('comment') or '—'}")

    document.add_heading("Подробные результаты", level=1)
    details_table = document.add_table(rows=1, cols=7)
    details_table.style = "Table Grid"
    for cell, value in zip(
        details_table.rows[0].cells,
        ("id", "Закон", "Вопрос", "Ожидалось", "Позиция", "top-10", "Результат"),
    ):
        cell.text = value
    for evaluation in evaluations:
        case = evaluation["case"]
        top_articles = ", ".join(
            normalize_article_number(result.get("article_number")) or "—"
            for result in evaluation["top_results"][:10]
        )
        values = (
            case["id"],
            case.get("law") or "",
            case.get("question") or "",
            ", ".join(case.get("expected_article_numbers", [])),
            str(evaluation["rank"] or "—"),
            top_articles,
            "успех" if evaluation["matched_result"] else "ошибка",
        )
        cells = details_table.add_row().cells
        for cell, value in zip(cells, values):
            cell.text = value

    document.add_heading("Вывод", level=1)
    for line in _conclusion_lines(summary, grouped_metrics, evaluations):
        document.add_paragraph(line, style="List Bullet")

    document.save(output_path)
    return True


def get_retrieval_search(retriever: Any, mode: str):
    if mode == "semantic":
        return retriever.search_semantic
    if mode == "hybrid":
        return retriever.search_hybrid
    raise ValueError(f"Unsupported retrieval mode: {mode}")


def run_evaluation(
    cases_path: Path,
    top_k: int,
    output_dir: Path,
    mode: str = "semantic",
) -> dict[str, Path]:
    from app.config import settings
    from app.db import (
        SessionLocal,
        check_database_connection,
        check_pgvector_extension,
    )
    from app.rag.embedder import Embedder
    from app.rag.retriever import Retriever

    if top_k < 1:
        raise RuntimeError("top_k must be greater than 0")

    cases = load_cases(cases_path)
    database_available = check_database_connection()
    pgvector_available = check_pgvector_extension()
    if not database_available:
        raise RuntimeError("Database is not available")

    db = SessionLocal()
    try:
        retriever = Retriever(db=db, embedder=Embedder())
        search = get_retrieval_search(retriever, mode)
        evaluations: list[dict[str, Any]] = []
        for index, case in enumerate(cases, start=1):
            print(f"[{index}/{len(cases)}] {case['id']}: {case['question']}")
            results = search(case["question"], top_k=top_k)
            evaluations.append(
                evaluate_case_results(case, results, top_k=top_k)
            )
    finally:
        db.close()

    summary = calculate_summary_metrics(evaluations)
    grouped_metrics = calculate_grouped_metrics(evaluations)
    metadata = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "top_k": top_k,
        "retrieval_mode": mode,
        "embedding_model": settings.embedding_model_name,
        "hybrid_semantic_weight": settings.hybrid_semantic_weight,
        "hybrid_keyword_weight": settings.hybrid_keyword_weight,
        "hybrid_metadata_weight": settings.hybrid_metadata_weight,
        "database_available": database_available,
        "pgvector_available": pgvector_available,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "csv": output_dir / "retrieval_results.csv",
        "json": output_dir / "retrieval_results.json",
        "markdown": output_dir / "retrieval_report.md",
        "docx": output_dir / "retrieval_report.docx",
    }
    write_csv_report(evaluations, paths["csv"], metadata)
    write_json_report(
        evaluations,
        summary,
        grouped_metrics,
        metadata,
        paths["json"],
    )
    paths["markdown"].write_text(
        build_markdown_report(
            evaluations,
            summary,
            grouped_metrics,
            metadata,
        ),
        encoding="utf-8",
    )
    write_docx_report(
        evaluations,
        summary,
        grouped_metrics,
        metadata,
        paths["docx"],
    )
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate LawyerChat retrieval on control questions."
    )
    parser.add_argument(
        "--cases",
        default="data/evaluation/retrieval_cases.json",
        help="Path to retrieval evaluation cases JSON",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Number of retrieval results per question",
    )
    parser.add_argument(
        "--mode",
        choices=("semantic", "hybrid"),
        default="semantic",
        help="Retrieval mode to evaluate",
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory for CSV, JSON, Markdown and DOCX reports",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = run_evaluation(
            cases_path=Path(args.cases),
            top_k=args.top_k,
            output_dir=Path(args.output_dir),
            mode=args.mode,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("Retrieval evaluation completed:")
    for report_type, path in paths.items():
        if path.exists():
            print(f"- {report_type}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
