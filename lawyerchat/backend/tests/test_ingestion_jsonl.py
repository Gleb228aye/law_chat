import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ["DEBUG"] = "true"
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://legal_user:legal_password@localhost:5433/legal_rag",
)

from app.rag.ingestion import _load_jsonl_chunks


class JsonlIngestionTests(unittest.TestCase):
    def test_jsonl_line_becomes_one_chunk(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "tk.jsonl"
            file_path.write_text(
                json.dumps(
                    {
                        "document_title": "Трудовой кодекс Российской Федерации",
                        "article_number": "80",
                        "article_title": "Расторжение трудового договора",
                        "text": "Работник имеет право расторгнуть трудовой договор.",
                        "referenced_articles": ["77"],
                        "section_title": "Раздел III",
                        "source_url": None,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            title, chunks, issues = _load_jsonl_chunks(file_path)

        self.assertEqual("Трудовой кодекс Российской Федерации", title)
        self.assertEqual([], issues)
        self.assertEqual(1, len(chunks))
        self.assertEqual(
            "Работник имеет право расторгнуть трудовой договор.",
            chunks[0]["content"],
        )
        self.assertEqual("80", chunks[0]["article_number"])
        self.assertEqual(["77"], chunks[0]["referenced_articles"])

    def test_invalid_and_empty_jsonl_records_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "broken.jsonl"
            lines = [
                '{"article_number": "77", "text": ""}',
                '{"article_number": "80", "text": "Valid text."}',
                '{"article_number": ',
            ]
            file_path.write_text("\n".join(lines), encoding="utf-8")

            title, chunks, issues = _load_jsonl_chunks(file_path)

        self.assertEqual("broken", title)
        self.assertEqual(1, len(chunks))
        self.assertEqual("Valid text.", chunks[0]["content"])
        self.assertEqual(2, len(issues))
        self.assertTrue(any("empty text" in issue for issue in issues))
        self.assertTrue(any("invalid JSON" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
