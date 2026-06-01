import unittest

from scripts.convert_html_to_jsonl import convert_html_to_records


class ConvertHtmlToJsonlTests(unittest.TestCase):
    def test_html_with_structure_and_articles_becomes_jsonl_records(self) -> None:
        html = """
        <html>
          <head>
            <style>.hidden { display: none; }</style>
            <script>window.x = 1;</script>
          </head>
          <body>
            <p>Раздел III. Трудовой договор</p>
            <p>Глава 13. Прекращение трудового договора</p>
            <p>Статья 77. Общие основания прекращения трудового договора</p>
            <p>Основания прекращения договора указаны также в статье 80.</p>
            <p>Статья 80. Расторжение трудового договора по инициативе работника</p>
            <p>Работник имеет право расторгнуть трудовой договор.</p>
          </body>
        </html>
        """

        records = convert_html_to_records(
            html,
            source_filename="tk.htm",
            document_id="tk_rf",
            document_title="Трудовой кодекс Российской Федерации",
        )

        self.assertEqual(2, len(records))
        self.assertEqual("77", records[0]["article_number"])
        self.assertEqual(
            "Общие основания прекращения трудового договора",
            records[0]["article_title"],
        )
        self.assertEqual("80", records[1]["article_number"])
        self.assertEqual(
            "Расторжение трудового договора по инициативе работника",
            records[1]["article_title"],
        )
        self.assertEqual("Раздел III. Трудовой договор", records[0]["section_title"])
        self.assertEqual(
            "Глава 13. Прекращение трудового договора",
            records[0]["chapter_title"],
        )
        self.assertTrue(records[0]["text"])
        self.assertEqual(["80"], records[0]["referenced_articles"])


if __name__ == "__main__":
    unittest.main()
