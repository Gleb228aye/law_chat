import unittest

from scripts.evaluate_retrieval import (
    calculate_question_type_metrics,
    calculate_summary_metrics,
    evaluate_case_results,
)


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
    def test_primary_source_match_counts_as_success(self) -> None:
        case = {
            "id": "new_001",
            "law": "Трудовой кодекс Российской Федерации",
            "question": "Вопрос",
            "expected_sources": [
                {
                    "document_id": "tk_rf",
                    "article_number": "80",
                    "relevance": "primary",
                    "reason": "Основная норма",
                }
            ],
        }

        evaluation = evaluate_case_results(
            case,
            [result("80", "Трудовой кодекс Российской Федерации")],
        )

        self.assertTrue(evaluation["hit_top_1"])
        self.assertEqual("primary", evaluation["matched_relevance"])
        self.assertFalse(evaluation["partial_match"])

    def test_secondary_source_match_counts_as_success(self) -> None:
        case = {
            "id": "new_002",
            "law": "Семейный кодекс Российской Федерации",
            "question": "Вопрос",
            "expected_sources": [
                {
                    "document_id": "sk_rf",
                    "article_number": "21",
                    "relevance": "secondary",
                    "reason": "Дополнительная релевантная норма",
                }
            ],
        }

        evaluation = evaluate_case_results(
            case,
            [result("21", "semeynyy_kodeks_rf")],
        )

        self.assertTrue(evaluation["hit_top_1"])
        self.assertEqual("secondary", evaluation["matched_relevance"])
        self.assertFalse(evaluation["partial_match"])

    def test_acceptable_source_is_partial_but_not_hit(self) -> None:
        case = {
            "id": "new_003",
            "law": "Защита прав потребителей",
            "question": "Вопрос",
            "expected_sources": [
                {
                    "document_id": "gk_rf",
                    "article_number": "475",
                    "relevance": "acceptable",
                    "reason": "Допустимая смежная норма",
                }
            ],
        }

        evaluation = evaluate_case_results(
            case,
            [result("475", "Гражданский кодекс Российской Федерации")],
        )

        self.assertFalse(evaluation["hit_top_1"])
        self.assertFalse(evaluation["hit_top_5"])
        self.assertIsNone(evaluation["rank"])
        self.assertEqual("acceptable", evaluation["matched_relevance"])
        self.assertTrue(evaluation["partial_match"])

    def test_legacy_expected_article_numbers_remain_supported(self) -> None:
        evaluation = evaluate_case_results(
            CASE,
            [result("80", "Трудовой кодекс Российской Федерации")],
        )

        self.assertTrue(evaluation["hit_top_1"])
        self.assertEqual("primary", evaluation["matched_relevance"])

    def test_question_type_metrics_group_scored_cases(self) -> None:
        case = {
            **CASE,
            "question_type": "rights",
        }
        evaluation = evaluate_case_results(
            case,
            [result("80", "Трудовой кодекс Российской Федерации")],
        )

        metrics = calculate_question_type_metrics([evaluation])

        self.assertEqual(1, metrics["rights"]["questions_count"])
        self.assertEqual(1.0, metrics["rights"]["top_5_accuracy"])

    def test_out_of_scope_case_is_not_strictly_evaluated(self) -> None:
        case = {
            "id": "neg_001",
            "case_type": "out_of_scope",
            "question": "Как оформить загранпаспорт?",
            "expected_behavior": "no_answer",
        }

        evaluation = evaluate_case_results(case, [], top_k=20)

        self.assertTrue(evaluation["not_evaluated"])
        self.assertIsNone(evaluation["hit_top_5"])
        self.assertIsNone(evaluation["reciprocal_rank"])

    def test_mean_rank_is_average_of_found_ranks(self) -> None:
        first = evaluate_case_results(
            CASE,
            [result("80", "Трудовой кодекс Российской Федерации")],
        )
        third = evaluate_case_results(
            CASE,
            [
                result("77", "Трудовой кодекс Российской Федерации"),
                result("81", "Трудовой кодекс Российской Федерации"),
                result("80", "Трудовой кодекс Российской Федерации"),
            ],
        )

        summary = calculate_summary_metrics([first, third])

        self.assertEqual(2.0, summary["mean_rank"])

    def test_document_recall_at_five_when_document_is_present(self) -> None:
        evaluation = evaluate_case_results(
            CASE,
            [
                result("10"),
                result("11", "Трудовой кодекс Российской Федерации"),
            ],
        )

        self.assertTrue(evaluation["document_hit_top_5"])

    def test_wrong_document_at_one_when_first_result_is_another_law(self) -> None:
        evaluation = evaluate_case_results(
            CASE,
            [
                result("80", "Семейный кодекс Российской Федерации"),
                result("80", "Трудовой кодекс Российской Федерации"),
            ],
        )

        self.assertTrue(evaluation["wrong_document_top_1"])

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
