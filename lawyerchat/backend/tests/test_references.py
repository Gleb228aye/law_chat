import unittest

from app.rag.references import extract_referenced_articles


class ReferenceExtractionTests(unittest.TestCase):
    def test_extracts_article_after_point_reference(self) -> None:
        self.assertEqual(
            ["81"],
            extract_referenced_articles("пункт 2 статьи 81 настоящего Кодекса"),
        )

    def test_extracts_article_after_part_reference(self) -> None:
        self.assertEqual(
            ["72"],
            extract_referenced_articles("часть вторая статьи 72 настоящего Кодекса"),
        )

    def test_extracts_multiple_articles(self) -> None:
        self.assertEqual(
            ["80", "81"],
            extract_referenced_articles("согласно статьях 80 и 81 настоящего Кодекса"),
        )

    def test_excludes_current_article(self) -> None:
        self.assertEqual(
            [],
            extract_referenced_articles(
                "статья 77 настоящего Кодекса",
                current_article_number="77",
            ),
        )

    def test_extracts_dotted_article_number(self) -> None:
        self.assertEqual(
            ["5.27"],
            extract_referenced_articles("ответственность предусмотрена статьей 5.27"),
        )


if __name__ == "__main__":
    unittest.main()
