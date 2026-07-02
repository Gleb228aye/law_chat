import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError


os.environ["DEBUG"] = "true"

from app.config import settings
from app.api.search import search_documents
from app.llm.rag_service import RAGChatService
from app.schemas.chat import ChatRequest
from app.schemas.search import SearchRequest


class RetrievalModeSchemaTests(unittest.TestCase):
    def test_mode_is_optional_for_legacy_requests(self) -> None:
        self.assertIsNone(ChatRequest(query="Вопрос").retrieval_mode)
        self.assertIsNone(SearchRequest(query="Вопрос").retrieval_mode)

    def test_both_modes_are_accepted(self) -> None:
        self.assertEqual(
            "semantic",
            ChatRequest(query="Вопрос", retrieval_mode="semantic").retrieval_mode,
        )
        self.assertEqual(
            "hybrid",
            SearchRequest(query="Вопрос", retrieval_mode="hybrid").retrieval_mode,
        )

    def test_unknown_mode_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ChatRequest(query="Вопрос", retrieval_mode="unknown")


class RAGChatRetrievalModeTests(unittest.TestCase):
    @patch("app.llm.rag_service.build_sources", return_value=[])
    @patch("app.llm.rag_service.build_rag_prompt", return_value="prompt")
    @patch("app.llm.rag_service.LLMClient")
    @patch("app.llm.rag_service.Retriever")
    @patch("app.llm.rag_service.Embedder")
    def test_explicit_mode_is_used_and_returned(
        self,
        embedder_class,
        retriever_class,
        llm_client_class,
        _build_prompt,
        _build_sources,
    ) -> None:
        retriever_class.return_value.search.return_value = []
        llm_client_class.return_value.generate_answer.return_value = "Ответ"

        with patch.object(settings, "llm_api_key", "test"):
            result = RAGChatService(db=object()).answer(
                query="Вопрос",
                top_k=5,
                retrieval_mode="semantic",
            )

        retriever_class.return_value.search.assert_called_once_with(
            query="Вопрос",
            top_k=5,
            retrieval_mode="semantic",
        )
        self.assertEqual("semantic", result["retrieval_mode"])
        embedder_class.assert_called_once_with()

    @patch("app.llm.rag_service.build_sources", return_value=[])
    @patch("app.llm.rag_service.build_rag_prompt", return_value="prompt")
    @patch("app.llm.rag_service.LLMClient")
    @patch("app.llm.rag_service.Retriever")
    @patch("app.llm.rag_service.Embedder")
    def test_missing_mode_uses_configured_default(
        self,
        _embedder_class,
        retriever_class,
        llm_client_class,
        _build_prompt,
        _build_sources,
    ) -> None:
        retriever_class.return_value.search.return_value = []
        llm_client_class.return_value.generate_answer.return_value = "Ответ"

        with (
            patch.object(settings, "llm_api_key", "test"),
            patch.object(settings, "retrieval_mode", "hybrid"),
        ):
            result = RAGChatService(db=object()).answer(
                query="Вопрос",
                top_k=5,
            )

        self.assertEqual("hybrid", result["retrieval_mode"])


class SearchEndpointRetrievalModeTests(unittest.TestCase):
    class FakeQuery:
        def limit(self, _limit):
            return self

        def count(self):
            return 1

    class FakeDB:
        def query(self, _model):
            return SearchEndpointRetrievalModeTests.FakeQuery()

    @patch("app.api.search.Retriever")
    @patch("app.api.search.Embedder")
    def test_search_uses_explicit_semantic_mode(
        self,
        _embedder_class,
        retriever_class,
    ) -> None:
        retriever_class.return_value.search.return_value = []

        response = search_documents(
            SearchRequest(query="Вопрос", retrieval_mode="semantic"),
            db=self.FakeDB(),
        )

        retriever_class.return_value.search.assert_called_once_with(
            query="Вопрос",
            top_k=5,
            retrieval_mode="semantic",
        )
        self.assertEqual("semantic", response.retrieval_mode)

    @patch("app.api.search.Retriever")
    @patch("app.api.search.Embedder")
    def test_search_without_mode_uses_backend_default(
        self,
        _embedder_class,
        retriever_class,
    ) -> None:
        retriever_class.return_value.search.return_value = []

        with patch.object(settings, "retrieval_mode", "hybrid"):
            response = search_documents(
                SearchRequest(query="Вопрос"),
                db=self.FakeDB(),
            )

        self.assertEqual("hybrid", response.retrieval_mode)


if __name__ == "__main__":
    unittest.main()
