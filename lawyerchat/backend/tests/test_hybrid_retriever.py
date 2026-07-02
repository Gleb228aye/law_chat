import unittest

from app.rag.retriever import (
    detect_law_hint,
    document_matches_law_hint,
    extract_article_number,
)
from scripts.evaluate_retrieval import build_parser, get_retrieval_search


class HybridRetrieverHelpersTests(unittest.TestCase):
    def test_extracts_article_number(self) -> None:
        self.assertEqual("18", extract_article_number("Что сказано в статье 18?"))

    def test_extracts_abbreviated_decimal_article_number(self) -> None:
        self.assertEqual("10.1", extract_article_number("по ст. 10.1"))

    def test_detects_consumer_protection_law(self) -> None:
        self.assertEqual(
            "zkpp_rf",
            detect_law_hint("права потребителя при недостатках товара"),
        )

    def test_family_law_aliases_match(self) -> None:
        self.assertTrue(document_matches_law_hint("semeynyy_kodeks_rf", "sk_rf"))
        self.assertTrue(document_matches_law_hint("sk_rf", "sk_rf"))


class EvaluationModeTests(unittest.TestCase):
    class FakeRetriever:
        def search(self, query: str, top_k: int = 5):
            raise AssertionError("generic search must not be used by explicit mode")

        def search_semantic(self, query: str, top_k: int = 5):
            return ["semantic", query, top_k]

        def search_hybrid(self, query: str, top_k: int = 5):
            return ["hybrid", query, top_k]

    def test_semantic_mode_uses_legacy_semantic_search(self) -> None:
        search = get_retrieval_search(self.FakeRetriever(), "semantic")
        self.assertEqual(["semantic", "query", 20], search("query", top_k=20))

    def test_hybrid_mode_uses_hybrid_search(self) -> None:
        search = get_retrieval_search(self.FakeRetriever(), "hybrid")
        self.assertEqual(["hybrid", "query", 20], search("query", top_k=20))

    def test_parser_accepts_both_modes(self) -> None:
        parser = build_parser()
        self.assertEqual("semantic", parser.parse_args(["--mode", "semantic"]).mode)
        self.assertEqual("hybrid", parser.parse_args(["--mode", "hybrid"]).mode)


if __name__ == "__main__":
    unittest.main()
