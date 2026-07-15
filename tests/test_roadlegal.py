import json
import unittest
from pathlib import Path

from roadlegal.challan import ChallanCalculator
from roadlegal.game_content import quiz_for
from roadlegal.geo import geofence
from roadlegal.prepared import apply_prepared_fallback, prepared_response
from roadlegal.rag import RoadLegalRAG


ROOT = Path(__file__).resolve().parents[1]
STATIC_DATA = ROOT / "web" / "static-data.json"
SERVICE_WORKER = ROOT / "web" / "sw.js"
INDEX_HTML = ROOT / "web" / "index.html"
WEB_APP = ROOT / "web" / "app.js"
HF_SPACE_APP = ROOT / "hf_space" / "app.py"


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
        self.assertEqual(rag.health()["answer_topics"], 200)
        self.assertTrue(rag.health()["prepared_fallback"])
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

    def test_generation_guard_allows_list_numbering_but_rejects_invented_fines(self):
        rag = RoadLegalRAG()
        results = rag.search("helmet Thailand", jurisdiction="thailand_national", k=2)
        fine = rag._maybe_calculate("helmet fine", "thailand_national")
        self.assertTrue(rag._generation_is_grounded("1. Wear a fastened helmet [S1].", results, fine))
        self.assertFalse(rag._generation_is_grounded("The fine is THB 9,999 [S1].", results, fine))
        self.assertFalse(rag._generation_is_grounded("[S1] Source title | status=verified_source [S2]", results, fine))

    def test_offline_demo_has_complete_country_answer_packs(self):
        payload = json.loads(STATIC_DATA.read_text(encoding="utf-8"))
        packs = payload["offline_answers"]
        required_topics = {
            "overspeeding",
            "no_helmet",
            "no_seatbelt",
            "drink_driving",
            "mobile_phone",
            "no_license",
            "documents",
            "cross_border",
            "emergency",
            "scenario",
            "no_insurance",
            "no_registration",
            "dangerous_driving",
            "parking",
            "traffic_signals",
            "pedestrian_safety",
            "child_restraints",
            "vehicle_condition",
            "fatigue",
            "weather",
            "road_signs",
            "overtaking",
            "road_rules_overview",
            "accident_duties",
            "ticket_payment",
        }

        self.assertEqual(len(packs), 8)
        self.assertEqual(payload["health"]["answer_topics"], 200)
        self.assertTrue(payload["health"]["offline_ready"])
        for jurisdiction, pack in packs.items():
            self.assertEqual(set(pack["answers"]), required_topics, jurisdiction)
            for topic, answer in pack["answers"].items():
                self.assertTrue(answer["summary"], f"{jurisdiction}:{topic}")
                self.assertTrue(answer["rules"], f"{jurisdiction}:{topic}")
                self.assertTrue(answer["actions"], f"{jurisdiction}:{topic}")
                self.assertTrue(answer["citations"], f"{jurisdiction}:{topic}")
                self.assertTrue(answer["keywords"], f"{jurisdiction}:{topic}")

    def test_prepared_answer_matching_covers_common_paraphrases_in_every_country(self):
        cases = {
            "How do I pay or appeal a traffic fine?": "ticket_payment",
            "What must I do after a road collision?": "accident_duties",
            "Does a small child need a booster seat?": "child_restraints",
            "How should I drive in monsoon rain and low visibility?": "weather",
            "Can I pass another vehicle near a blind curve?": "overtaking",
            "What should I do when I am too tired to drive?": "fatigue",
        }
        jurisdictions = json.loads(STATIC_DATA.read_text(encoding="utf-8"))["offline_answers"]
        for jurisdiction in jurisdictions:
            for question, topic in cases.items():
                response = prepared_response(question, jurisdiction)
                self.assertIsNotNone(response, f"{jurisdiction}:{question}")
                self.assertEqual(response["matched_topic"], topic, f"{jurisdiction}:{question}")
                self.assertTrue(response["citations"])

    def test_unavailable_live_model_uses_prepared_answer(self):
        weak_live_response = {
            "answer": "I do not have enough local source material.",
            "citations": [],
            "fine": None,
            "model": {"loaded": False, "mode": "extractive-rag"},
        }
        response = apply_prepared_fallback(
            weak_live_response,
            "What are the helmet rules?",
            "thailand_national",
        )
        self.assertTrue(response["live_fallback"])
        self.assertEqual(response["mode"], "prepared-fallback")
        self.assertEqual(response["matched_topic"], "no_helmet")
        self.assertTrue(response["prepared"]["summary"])

    def test_every_country_has_a_complete_learning_quiz(self):
        payload = json.loads(STATIC_DATA.read_text(encoding="utf-8"))
        self.assertEqual(set(payload["quizzes"]), set(payload["offline_answers"]))
        for jurisdiction, quiz in payload["quizzes"].items():
            self.assertGreaterEqual(len(quiz["questions"]), 5, jurisdiction)
            for question in quiz["questions"]:
                self.assertIn(question["answer"], range(len(question["options"])))
                self.assertTrue(question["explanation"])

    def test_progressive_quiz_controls_and_feedback_are_packaged(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        script = WEB_APP.read_text(encoding="utf-8")
        self.assertNotIn("demoButton", html)
        self.assertNotIn("Run judge demo", html)
        self.assertIn('id="restartQuizButton"', html)
        self.assertIn('id="levelBadge"', html)
        self.assertIn("Challan / Ticket", html)
        self.assertIn("You are learning very well", script)
        self.assertIn("The correct answer is", script)
        self.assertIn("Badge unlocked: Learning Level", script)
        self.assertIn("Math.floor(score / 50)", script)
        self.assertIn('state.score = 0', script)
        self.assertIn('localStorage.setItem("roadlegal_score", "0")', script)
        self.assertIn("Your score and learning level were reset", script)
        self.assertIn("liveResponseNeedsPreparedFallback", script)
        self.assertIn("Live AI was unavailable or did not return a sufficiently grounded answer", script)

    def test_service_worker_caches_the_complete_demo(self):
        worker = SERVICE_WORKER.read_text(encoding="utf-8")
        for asset in (
            "./",
            "./index.html",
            "./styles.css",
            "./app.js",
            "./config.js",
            "./static-data.json",
            "./vendor/lucide.min.js",
        ):
            self.assertIn(asset, worker)
        self.assertIn("caches.open", worker)
        self.assertIn("self.skipWaiting", worker)

    def test_hugging_face_space_exposes_live_ai_contract(self):
        source = HF_SPACE_APP.read_text(encoding="utf-8")
        self.assertIn('MODEL_ID = os.environ.get("ROADLEGAL_TRANSFORMERS_MODEL", "Qwen/Qwen3-0.6B")', source)
        self.assertIn('@app.get("/api/health")', source)
        self.assertIn('@app.post("/api/chat")', source)
        self.assertIn('@app.post("/api/calculate-challan")', source)
        self.assertIn("RAG.llm = TransformersRuntime()", source)
        self.assertIn("app = gr.Server()", source)
        self.assertIn('@app.api(name="chat", concurrency_limit=1)', source)
        self.assertIn("apply_prepared_fallback", source)
        self.assertIn("_answer_with_fallback", source)


if __name__ == "__main__":
    unittest.main()
