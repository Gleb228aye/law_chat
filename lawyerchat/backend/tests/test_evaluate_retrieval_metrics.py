import unittest

from scripts.evaluate_retrieval import evaluate_case_results


CASE = {
    "id": "tk_001",
    "law": "Трудовой кодекс Российской Федерации",
    "expected_document_id": "tk_rf",
    "expected_document_title": "Трудовой кодекс Российской Федерации",
    "expected_article_numbers": ["80"],
    "question": "Как уволиться по собственному желанию?",
}


def result(article_number: str, document_title: str = "Другой кодекс") -> dict:
    return {
        "article_number": article_number,
        "document_title": document_title,
        "similarity": 0.8,
        "distance": 0.2,
    }


class RetrievalMetricsTests(unittest.TestCase):
    def test_transliterated_document_alias_matches_expected_document_id(self) -> None:
        case = {
            "id": "sk_002",
            "law": "Семейный кодекс Российской Федерации",
            "expected_document_id": "sk_rf",
            "expected_document_title": "Семейный кодекс Российской Федерации",
            "expected_article_numbers": ["12"],
            "question": "Какие условия необходимы для заключения брака?",
        }

        evaluation = evaluate_case_results(
            case,
            [result("12", "semeynyy_kodeks_rf")],
        )

        self.assertTrue(evaluation["hit_top_1"])
        self.assertEqual(1, evaluation["rank"])

    def test_expected_article_at_rank_one(self) -> None:
        evaluation = evaluate_case_results(
            CASE,
            [result("80", "Трудовой кодекс Российской Федерации")],
        )

        self.assertTrue(evaluation["hit_top_1"])
        self.assertTrue(evaluation["hit_top_3"])
        self.assertTrue(evaluation["hit_top_5"])
        self.assertEqual(1, evaluation["rank"])
        self.assertEqual(1.0, evaluation["reciprocal_rank"])

    def test_expected_article_at_rank_three(self) -> None:
        evaluation = evaluate_case_results(
            CASE,
            [
                result("80"),
                result("77", "Трудовой кодекс Российской Федерации"),
                result("80", "Трудовой кодекс Российской Федерации"),
            ],
        )

        self.assertFalse(evaluation["hit_top_1"])
        self.assertTrue(evaluation["hit_top_3"])
        self.assertTrue(evaluation["hit_top_5"])
        self.assertEqual(3, evaluation["rank"])
        self.assertAlmostEqual(1 / 3, evaluation["reciprocal_rank"])

    def test_expected_article_at_rank_ten(self) -> None:
        results = [
            result(str(200 + index), "Трудовой кодекс Российской Федерации")
            for index in range(9)
        ]
        results.append(result("80", "Трудовой кодекс Российской Федерации"))

        evaluation = evaluate_case_results(CASE, results, top_k=20)

        self.assertFalse(evaluation["hit_top_5"])
        self.assertTrue(evaluation["hit_top_10"])
        self.assertTrue(evaluation["hit_top_20"])
        self.assertEqual(10, evaluation["rank"])

    def test_expected_article_at_rank_fifteen(self) -> None:
        results = [
            result(str(200 + index), "Трудовой кодекс Российской Федерации")
            for index in range(14)
        ]
        results.append(result("80", "Трудовой кодекс Российской Федерации"))

        evaluation = evaluate_case_results(CASE, results, top_k=20)

        self.assertFalse(evaluation["hit_top_10"])
        self.assertTrue(evaluation["hit_top_20"])
        self.assertEqual(15, evaluation["rank"])

    def test_metrics_deeper_than_requested_top_k_are_not_calculated(self) -> None:
        evaluation = evaluate_case_results(
            CASE,
            [result("80", "Трудовой кодекс Российской Федерации")],
            top_k=5,
        )

        self.assertTrue(evaluation["hit_top_5"])
        self.assertIsNone(evaluation["hit_top_10"])
        self.assertIsNone(evaluation["hit_top_20"])

    def test_expected_article_is_missing(self) -> None:
        evaluation = evaluate_case_results(
            CASE,
            [
                result("77", "Трудовой кодекс Российской Федерации"),
                result("81", "Трудовой кодекс Российской Федерации"),
            ],
        )

        self.assertFalse(evaluation["hit_top_1"])
        self.assertFalse(evaluation["hit_top_3"])
        self.assertFalse(evaluation["hit_top_5"])
        self.assertFalse(evaluation["hit_top_10"])
        self.assertFalse(evaluation["hit_top_20"])
        self.assertIsNone(evaluation["rank"])
        self.assertEqual(0.0, evaluation["reciprocal_rank"])


if __name__ == "__main__":
    unittest.main()
