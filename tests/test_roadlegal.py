import unittest

from roadlegal.challan import ChallanCalculator
from roadlegal.game_content import quiz_for
from roadlegal.geo import geofence
from roadlegal.rag import RoadLegalRAG


class RoadLegalTests(unittest.TestCase):
    def test_india_overspeeding_fine(self):
        calculator = ChallanCalculator()
        result = calculator.calculate("india_national", "overspeeding", "light_motor_vehicle")
        self.assertEqual(result.status, "verified")
        self.assertIn("Rs", result.amount_display)
        self.assertIn("183", result.legal_basis)

    def test_unknown_country_fine_is_cautious(self):
        calculator = ChallanCalculator()
        result = calculator.calculate("bangladesh_national", "overspeeding", "any")
        self.assertEqual(result.status, "needs_review")
        self.assertIn("requires", result.amount_display.lower())

    def test_geofence_bangladesh(self):
        result = geofence(23.8, 90.4)
        self.assertTrue(result["matched"])
        self.assertEqual(result["jurisdiction"], "bangladesh_national")

    def test_rag_returns_citations(self):
        rag = RoadLegalRAG()
        answer = rag.answer("What is the fine for overspeeding in India?", jurisdiction="india_national")
        self.assertIn("answer", answer)
        self.assertGreaterEqual(len(answer["citations"]), 1)
        self.assertIn(answer["mode"], {"extractive-rag", "generative-rag"})

    def test_thailand_has_expanded_law_and_game_content(self):
        calculator = ChallanCalculator()
        offences = {item["id"] for item in calculator.offences("thailand_national")}
        self.assertIn("no_helmet", offences)
        self.assertIn("drink_driving", offences)
        quiz = quiz_for("thailand_national")
        self.assertGreaterEqual(len(quiz["questions"]), 5)
        self.assertTrue(any("Thailand scenario" in item["question"] for item in quiz["questions"]))

    def test_thailand_official_maximum_fines(self):
        calculator = ChallanCalculator()
        helmet = calculator.calculate("thailand_national", "no helmet", "two_wheeler")
        speed = calculator.calculate("thailand_national", "speeding", "light_motor_vehicle")
        self.assertEqual(helmet.status, "verified")
        self.assertEqual(helmet.amount_display, "Up to THB 2,000")
        self.assertEqual(speed.amount_display, "Up to THB 4,000")
        self.assertIn("prd.go.th", helmet.source)

    def test_rag_isolates_selected_country(self):
        rag = RoadLegalRAG()
        results = rag.search("helmet fine and traffic law", jurisdiction="thailand_national", k=5)
        self.assertTrue(results)
        self.assertTrue(all(item["jurisdiction"] in {"thailand_national", "global", "bimstec"} for item in results))
        self.assertEqual(results[0]["source_title"], "Thailand PRD traffic penalties effective September 2022")

    def test_thai_query_expansion_retrieves_helmet_sources(self):
        rag = RoadLegalRAG()
        results = rag.search("ไม่สวมหมวกกันน็อก ปรับเท่าไหร่", jurisdiction="thailand_national", k=5)
        self.assertTrue(any("helmet" in item["tags"] or "no_helmet" in item["tags"] for item in results))
        self.assertFalse(any(item["jurisdiction"] == "india_national" for item in results))

    def test_thai_extractive_snippet_focuses_on_helmet_clause(self):
        rag = RoadLegalRAG()
        response = rag.answer("ไม่สวมหมวกกันน็อก ปรับเท่าไหร่", "thailand_national", "Thai")
        grounded = response["answer"].split("Grounded answer:", 1)[1]
        first_snippet = grounded.splitlines()[1]
        self.assertIn("หมวก", first_snippet)
        self.assertNotIn("ผิดครั้งแรกจำคุก", first_snippet)

    def test_generation_guard_rejects_unsupported_consequence(self):
        rag = RoadLegalRAG()
        results = rag.search("Thailand overspeeding rules", jurisdiction="thailand_national", k=2)
        fine = rag._maybe_calculate("Thailand overspeeding rules", "thailand_national")
        self.assertFalse(rag._generation_is_grounded("Speeding leads to imprisonment [S1].", results, fine))


if __name__ == "__main__":
    unittest.main()
