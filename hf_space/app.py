from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import time
import zipfile
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from typing import Any

import gradio as gr
import requests
import torch
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from transformers import AutoModelForCausalLM, AutoTokenizer


SOURCE_ARCHIVE = os.environ.get(
    "ROADLEGAL_SOURCE_ARCHIVE",
    "https://github.com/HopeChanphot/roadlegal/archive/refs/heads/main.zip",
)
SOURCE_DIR = Path("/tmp/roadlegal-source")
MODEL_ID = os.environ.get("ROADLEGAL_TRANSFORMERS_MODEL", "Qwen/Qwen3-0.6B")


def _prepare_source() -> Path:
    marker = SOURCE_DIR / "roadlegal" / "rag.py"
    if marker.exists():
        return SOURCE_DIR
    response = requests.get(SOURCE_ARCHIVE, timeout=120)
    response.raise_for_status()
    staging = SOURCE_DIR.with_name("roadlegal-source-staging")
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        archive.extractall(staging)
    roots = [path for path in staging.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise RuntimeError("RoadLegal source archive did not contain one project root")
    shutil.rmtree(SOURCE_DIR, ignore_errors=True)
    roots[0].rename(SOURCE_DIR)
    shutil.rmtree(staging, ignore_errors=True)
    return SOURCE_DIR


PROJECT_ROOT = _prepare_source()
sys.path.insert(0, str(PROJECT_ROOT))

from roadlegal.challan import ChallanCalculator  # noqa: E402
from roadlegal.game_content import quiz_for  # noqa: E402
from roadlegal.geo import geofence  # noqa: E402
from roadlegal.llm_runtime import ModelStatus  # noqa: E402
from roadlegal.prepared import apply_prepared_fallback  # noqa: E402
from roadlegal.rag import RoadLegalRAG  # noqa: E402


_tokenizer: Any | None = None
_model: Any | None = None
_model_error: str | None = None
_load_seconds: float | None = None
_model_lock = threading.RLock()


def _load_model() -> bool:
    global _tokenizer, _model, _model_error, _load_seconds
    if _model is not None:
        return True
    with _model_lock:
        if _model is not None:
            return True
        started = time.perf_counter()
        try:
            _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
            _model = AutoModelForCausalLM.from_pretrained(
                MODEL_ID,
                dtype=torch.float32,
            )
            _model.to("cpu")
            _model.eval()
            _load_seconds = round(time.perf_counter() - started, 3)
            _model_error = None
            return True
        except Exception as exc:
            _model = None
            _model_error = f"{type(exc).__name__}: {exc}"
            return False


def _generate_impl(prompt: str, max_tokens: int) -> str | None:
    if not _load_model() or _model is None or _tokenizer is None:
        return None
    messages = [
        {
            "role": "system",
            "content": "You are RoadLegal. Answer only from the supplied sources. Cite source labels. Do not invent fines or consequences.",
        },
        {"role": "user", "content": prompt},
    ]
    rendered = _tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    inputs = _tokenizer([rendered], return_tensors="pt").to(_model.device)
    with _model_lock, torch.inference_mode():
        output = _model.generate(
            **inputs,
            max_new_tokens=min(max_tokens, 256),
            do_sample=False,
            repetition_penalty=1.08,
            pad_token_id=_tokenizer.eos_token_id,
        )
    generated = output[0][inputs.input_ids.shape[1] :]
    text = _tokenizer.decode(generated, skip_special_tokens=True).strip()
    return text if len(text) >= 12 else None


class TransformersRuntime:
    def status(self) -> ModelStatus:
        loaded = _model is not None
        if loaded:
            mode = "generative-rag"
            note = "Qwen3-0.6B is loaded through Transformers on the Hugging Face Space."
        elif _model_error:
            mode = "extractive-rag"
            note = f"Qwen could not load; extractive RAG remains available. {_model_error}"
        else:
            mode = "model-loading"
            note = "Qwen3-0.6B is warming; extractive RAG remains available."
        return ModelStatus(
            mode=mode,
            engine="transformers" if loaded else None,
            model=MODEL_ID,
            llama_cli=None,
            llama_server=None,
            gguf_model=None,
            cached_hf_model=MODEL_ID if loaded else None,
            loaded=loaded,
            load_seconds=_load_seconds,
            note=note,
        )

    def warmup(self) -> bool:
        return _load_model()

    def generate(self, prompt: str, max_tokens: int = 128, timeout: int = 75) -> str | None:
        del timeout
        return _generate_impl(prompt, max_tokens)


RAG = RoadLegalRAG()
RAG.llm = TransformersRuntime()
CALCULATOR = ChallanCalculator()


def _answer_with_fallback(message: str, jurisdiction: str, language: str) -> dict[str, Any]:
    result = RAG.answer(message, jurisdiction=jurisdiction, language=language)
    return apply_prepared_fallback(result, message, jurisdiction, language)

app = gr.Server()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/", response_class=HTMLResponse)
def homepage() -> str:
    return """
    <!doctype html>
    <html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>RoadLegal AI Backend</title>
    <style>
      body{font:16px/1.55 system-ui,sans-serif;max-width:760px;margin:8vh auto;padding:24px;color:#17342d}
      h1{font-size:2rem} code{background:#eef5f1;padding:3px 6px;border-radius:4px} a{color:#087b61}
    </style></head><body>
    <h1>RoadLegal AI Backend</h1>
    <p>Qwen3-0.6B with jurisdiction-filtered legal retrieval for the BIMSTEC Road Safety Hackathon.</p>
    <p>Use the complete interface at <a href="https://hopechanphot.github.io/roadlegal/">RoadLegal on GitHub Pages</a>.</p>
    <p>Service status: <a href="/api/health"><code>/api/health</code></a></p>
    </body></html>
    """


@app.get("/api/health")
def health() -> dict[str, Any]:
    payload = RAG.health()
    payload["cloud"] = {"provider": "hugging-face-spaces", "sdk": "gradio", "model": MODEL_ID}
    return payload


@app.get("/api/jurisdictions")
def jurisdictions() -> dict[str, Any]:
    return {"jurisdictions": CALCULATOR.jurisdictions()}


@app.get("/api/offences")
def offences(jurisdiction: str = "india_national") -> dict[str, Any]:
    return {"offences": CALCULATOR.offences(jurisdiction)}


@app.get("/api/geofence")
def location(lat: float, lon: float) -> dict[str, Any]:
    return geofence(lat, lon)


@app.get("/api/quiz")
def quiz(jurisdiction: str = "india_national") -> dict[str, Any]:
    return quiz_for(jurisdiction)


@app.get("/api/search")
def search(q: str, jurisdiction: str = "india_national") -> dict[str, Any]:
    if not q.strip():
        raise HTTPException(status_code=400, detail="q is required")
    results, diagnostics = RAG.search_with_diagnostics(q, jurisdiction=jurisdiction)
    return {"results": results, "retrieval": diagnostics}


@app.post("/api/chat")
def chat(payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message", "")).strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    jurisdiction = str(payload.get("jurisdiction", "india_national"))
    language = str(payload.get("language", "English"))
    return _answer_with_fallback(message, jurisdiction, language)


def _gradio_chat_impl(message: str, jurisdiction: str, language: str) -> str:
    result = _answer_with_fallback(message.strip(), jurisdiction, language)
    return json.dumps(result, ensure_ascii=False)


@app.api(name="chat", concurrency_limit=1)
def gradio_chat(message: str, jurisdiction: str, language: str = "English") -> str:
    """Answer a traffic-law question with Qwen and retrieved legal sources."""
    return _gradio_chat_impl(message, jurisdiction, language)


try:
    import spaces

    @spaces.GPU(duration=1)
    def zero_gpu_capability_probe() -> str:
        """Satisfy ZeroGPU hosting while public chat remains on the CPU path."""
        return "RoadLegal public chat uses quota-free CPU inference."
except ImportError:
    pass


@app.post("/api/calculate-challan")
def calculate(payload: dict[str, Any]) -> dict[str, Any]:
    result = CALCULATOR.calculate(
        str(payload.get("jurisdiction", "india_national")),
        str(payload.get("offence", "")),
        str(payload.get("vehicle_class", "light_motor_vehicle")),
    )
    return asdict(result)


@app.post("/api/feedback")
def feedback(payload: dict[str, Any]) -> dict[str, Any]:
    print("RoadLegal feedback:", json.dumps(payload, ensure_ascii=False))
    return {"ok": True}


if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "7860")),
        show_error=True,
    )
