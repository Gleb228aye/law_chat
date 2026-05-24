import unittest

from app.llm.prompt_builder import build_rag_prompt


class PromptBuilderTests(unittest.TestCase):
    def test_prompt_contains_required_rag_information(self) -> None:
        prompt = build_rag_prompt(
            query="Когда можно расторгнуть трудовой договор?",
            chunks=[
                {
                    "filename": "Trudovoj-kodeks-Rossijskoj-Federatsii.txt",
                    "chunk_index": 114,
                    "content": "Основания прекращения трудового договора...",
                    "article_number": "77",
                    "article_title": "Общие основания прекращения трудового договора",
                    "referenced_articles": ["80", "81"],
                }
            ],
        )

        self.assertIn("Когда можно расторгнуть трудовой договор?", prompt)
        self.assertIn("Статья: 77", prompt)
        self.assertIn("Общие основания прекращения трудового договора", prompt)
        self.assertIn("Ссылки на статьи: 80, 81", prompt)
        self.assertIn("Не используй сведения вне контекста", prompt)


if __name__ == "__main__":
    unittest.main()
