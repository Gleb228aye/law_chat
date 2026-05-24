import unittest

from app.rag.splitter import split_legal_text


class LegalSplitterTests(unittest.TestCase):
    def test_form_feed_is_removed_before_chunking(self) -> None:
        chunks = split_legal_text(
            "Статья 1. Первая статья\nТекст.\f\nСтатья 2. Вторая статья\nТекст.",
            chunk_size=300,
            chunk_overlap=0,
        )

        self.assertFalse(any("\f" in chunk["content"] for chunk in chunks))

    def test_articles_have_their_own_numbers(self) -> None:
        chunks = split_legal_text(
            "Вводный текст.\n\nСтатья 1. Первая статья\nТекст первой статьи.\n"
            "Статья 2. Вторая статья\nТекст второй статьи.",
            chunk_size=300,
            chunk_overlap=0,
        )

        article_chunks = [chunk for chunk in chunks if chunk["article_number"]]
        self.assertEqual(["1", "2"], [chunk["article_number"] for chunk in article_chunks])
        self.assertIsNone(chunks[0]["article_number"])

    def test_long_article_chunks_keep_article_metadata(self) -> None:
        chunks = split_legal_text(
            "Статья 7. Длинная статья\n"
            + "Длинное предложение для проверки разбиения. " * 20,
            chunk_size=140,
            chunk_overlap=0,
        )

        self.assertGreater(len(chunks), 1)
        self.assertEqual({"7"}, {chunk["article_number"] for chunk in chunks})
        self.assertEqual(
            {"Длинная статья"},
            {chunk["article_title"] for chunk in chunks},
        )

    def test_wrapped_article_title_is_collected(self) -> None:
        chunks = split_legal_text(
            "Статья 77. Общие основания прекращения трудового договора и иных "
            "отношений\nсвязанных с работой\nТрудовой договор прекращается.",
            chunk_size=400,
            chunk_overlap=0,
        )

        self.assertEqual(
            "Общие основания прекращения трудового договора и иных отношений "
            "связанных с работой",
            chunks[0]["article_title"],
        )
        self.assertNotIn("Трудовой договор", chunks[0]["article_title"])

    def test_next_article_is_not_kept_in_previous_article_chunk(self) -> None:
        chunks = split_legal_text(
            "Статья 1. Первая статья\nСодержание первой статьи.\n"
            "\fСтатья 2. Вторая статья\nСодержание второй статьи.",
            chunk_size=400,
            chunk_overlap=0,
        )

        first_article = next(chunk for chunk in chunks if chunk["article_number"] == "1")
        self.assertNotIn("Статья 2", first_article["content"])

    def test_legal_overlap_does_not_create_word_fragments(self) -> None:
        chunks = split_legal_text(
            "Статья 2. Основные принципы правового регулирования\n"
            + "Свобода труда и право на отдых гарантируются работникам. " * 12,
            chunk_size=160,
            chunk_overlap=80,
        )

        self.assertGreater(len(chunks), 1)
        self.assertFalse(any(chunk["content"].startswith("а на отдых") for chunk in chunks))
        self.assertFalse(any(chunk["content"].startswith("тношений") for chunk in chunks))

    def test_wrapped_title_is_not_split_into_separate_heading_chunk(self) -> None:
        chunks = split_legal_text(
            "Статья 5. Трудовое законодательство и иные нормативные правовые акты, "
            "содержащие нормы трудового\nправа\n\n"
            "Регулирование трудовых отношений осуществляется настоящим Кодексом. "
            "Нормы трудового права применяются с учетом федеральных законов.",
            chunk_size=180,
            chunk_overlap=0,
        )

        self.assertIn("Регулирование трудовых отношений", chunks[0]["content"])
        self.assertFalse(
            len(chunks) > 1
            and chunks[0]["content"].startswith("Статья 5.")
            and "Регулирование трудовых отношений" not in chunks[0]["content"]
        )


if __name__ == "__main__":
    unittest.main()
