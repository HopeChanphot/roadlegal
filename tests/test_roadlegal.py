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


if __name__ == "__main__":
    unittest.main()
