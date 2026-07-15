from __future__ import annotations

import argparse
import json
import mimetypes
import os
import threading
from dataclasses import asdict
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .challan import ChallanCalculator
from .game_content import quiz_for
from .geo import geofence
from .paths import FEEDBACK_LOG, WEB_DIR
from .prepared import apply_prepared_fallback
from .rag import RoadLegalRAG


RAG = RoadLegalRAG()
CALCULATOR = ChallanCalculator()


class RoadLegalHandler(SimpleHTTPRequestHandler):
    server_version = "RoadLegal/0.2"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._json(RAG.health())
            return
        if parsed.path == "/api/jurisdictions":
            self._json({"jurisdictions": CALCULATOR.jurisdictions()})
            return
        if parsed.path == "/api/offences":
            query = parse_qs(parsed.query)
            jurisdiction = query.get("jurisdiction", ["india_national"])[0]
            self._json({"offences": CALCULATOR.offences(jurisdiction)})
            return
        if parsed.path == "/api/geofence":
            query = parse_qs(parsed.query)
            try:
                lat = float(query.get("lat", ["0"])[0])
                lon = float(query.get("lon", ["0"])[0])
            except ValueError:
                self._json({"error": "lat and lon must be numbers"}, HTTPStatus.BAD_REQUEST)
                return
            self._json(geofence(lat, lon))
            return
        if parsed.path == "/api/quiz":
            query = parse_qs(parsed.query)
            jurisdiction = query.get("jurisdiction", ["india_national"])[0]
            self._json(quiz_for(jurisdiction))
            return
        if parsed.path == "/api/search":
            query = parse_qs(parsed.query)
            message = query.get("q", [""])[0].strip()
            jurisdiction = query.get("jurisdiction", ["india_national"])[0]
            if not message:
                self._json({"error": "q is required"}, HTTPStatus.BAD_REQUEST)
                return
            results, diagnostics = RAG.search_with_diagnostics(message, jurisdiction=jurisdiction)
            self._json({"results": results, "retrieval": diagnostics})
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        payload = self._read_json()
        if parsed.path == "/api/chat":
            message = str(payload.get("message", "")).strip()
            if not message:
                self._json({"error": "message is required"}, HTTPStatus.BAD_REQUEST)
                return
            jurisdiction = str(payload.get("jurisdiction", "india_national"))
            language = str(payload.get("language", "English"))
            result = RAG.answer(message, jurisdiction=jurisdiction, language=language)
            self._json(apply_prepared_fallback(result, message, jurisdiction, language))
            return
        if parsed.path == "/api/calculate-challan":
            result = CALCULATOR.calculate(
                str(payload.get("jurisdiction", "india_national")),
                str(payload.get("offence", "")),
                str(payload.get("vehicle_class", "light_motor_vehicle")),
            )
            self._json(asdict(result))
            return
        if parsed.path == "/api/feedback":
            self._save_feedback(payload)
            self._json({"ok": True})
            return
        self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors_headers()
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, request_path: str) -> None:
        target = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        path = (WEB_DIR / target).resolve()
        if not str(path).startswith(str(WEB_DIR.resolve())) or not path.exists() or path.is_dir():
            path = WEB_DIR / "index.html"
        content = path.read_bytes()
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _cors_headers(self) -> None:
        allowed = os.environ.get("ROADLEGAL_CORS_ORIGIN", "*")
        self.send_header("Access-Control-Allow-Origin", allowed)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")

    def _save_feedback(self, payload: dict) -> None:
        FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
        with FEEDBACK_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

def main() -> None:
    parser = argparse.ArgumentParser(description="Run RoadLegal local web app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=int(os.environ.get("PORT", "8000")), type=int)
    args = parser.parse_args()
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), RoadLegalHandler)
    if os.environ.get("ROADLEGAL_WARM_MODEL", "").lower() in {"1", "true", "yes", "on"}:
        threading.Thread(target=RAG.llm.warmup, name="roadlegal-model-warmup", daemon=True).start()
    print(f"RoadLegal running at http://{args.host}:{args.port}")
    print(json.dumps(RAG.health(), indent=2))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping RoadLegal")


if __name__ == "__main__":
    main()
