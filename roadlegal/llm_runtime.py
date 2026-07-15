from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import MODELS_DIR


KNOWN_LLAMA_DIR = Path(r"C:\Program Files\llama-b4907-bin-win-cuda-cu12.4-x64")
KNOWN_HF_LLAMA = Path.home() / ".cache" / "huggingface" / "hub" / "models--meta-llama--Llama-3.2-3B-Instruct"
DEFAULT_MODEL_REPO = "Qwen/Qwen3-0.6B-GGUF"
DEFAULT_MODEL_FILE = "Qwen3-0.6B-Q8_0.gguf"


@dataclass
class ModelStatus:
    mode: str
    engine: str | None
    model: str | None
    llama_cli: str | None
    llama_server: str | None
    gguf_model: str | None
    cached_hf_model: str | None
    loaded: bool
    load_seconds: float | None
    note: str


def _truthy(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _find_executable(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    candidate = KNOWN_LLAMA_DIR / f"{name}.exe"
    if candidate.exists():
        return str(candidate)
    return None


def _find_gguf_model() -> str | None:
    configured = os.environ.get("ROADLEGAL_GGUF_MODEL")
    if configured and Path(configured).exists():
        return configured
    if MODELS_DIR.exists():
        candidates = sorted(MODELS_DIR.glob("*.gguf"), key=lambda path: path.stat().st_size)
        if candidates:
            return str(candidates[-1])
    return None


class LocalLLMRuntime:
    """Persistent llama.cpp generation with a cautious extractive fallback."""

    def __init__(self) -> None:
        self.llama_cli = _find_executable("llama-cli")
        self.llama_server = _find_executable("llama-server")
        self.gguf_model = _find_gguf_model()
        self.cached_hf_model = str(KNOWN_HF_LLAMA) if KNOWN_HF_LLAMA.exists() else None
        self.model_repo = os.environ.get("ROADLEGAL_MODEL_REPO", DEFAULT_MODEL_REPO)
        self.model_file = os.environ.get("ROADLEGAL_MODEL_FILE", DEFAULT_MODEL_FILE)
        self.auto_download = _truthy("ROADLEGAL_AUTO_DOWNLOAD_MODEL")
        self.binding_available = importlib.util.find_spec("llama_cpp") is not None
        self._llm: Any | None = None
        self._load_seconds: float | None = None
        self._last_error: str | None = None
        self._lock = threading.RLock()

    def status(self) -> ModelStatus:
        model_path = self.gguf_model or _find_gguf_model()
        if model_path:
            self.gguf_model = model_path
        if model_path and self.binding_available:
            note = "Persistent in-process llama.cpp generation is ready."
            mode = "generative-rag"
            engine = "llama-cpp-python"
        elif model_path and self.llama_cli:
            note = "GGUF generation is available through llama-cli; in-process bindings would reduce repeated model loading."
            mode = "generative-rag"
            engine = "llama-cli"
        elif self.auto_download and self.binding_available:
            note = "The cloud model is configured and will download/load during warm-up."
            mode = "model-loading"
            engine = "llama-cpp-python"
        elif self.cached_hf_model:
            note = "Cached Hugging Face weights were found, but this runtime needs a GGUF model."
            mode = "extractive-rag"
            engine = None
        elif self.llama_cli:
            note = "llama-cli was found, but no GGUF model is configured."
            mode = "extractive-rag"
            engine = None
        else:
            note = "No runnable llama.cpp engine and GGUF model were found."
            mode = "extractive-rag"
            engine = None
        if self._last_error:
            note = f"{note} Last model error: {self._last_error}"
        return ModelStatus(
            mode=mode,
            engine=engine,
            model=f"{self.model_repo}:{self.model_file}" if self.auto_download else (Path(model_path).name if model_path else None),
            llama_cli=self.llama_cli,
            llama_server=self.llama_server,
            gguf_model=model_path,
            cached_hf_model=self.cached_hf_model,
            loaded=self._llm is not None,
            load_seconds=self._load_seconds,
            note=note,
        )

    def warmup(self) -> bool:
        try:
            return self._load_in_process() is not None
        except Exception as exc:  # Runtime must never prevent extractive answers.
            self._last_error = f"{type(exc).__name__}: {exc}"
            return False

    def generate(self, prompt: str, max_tokens: int = 128, timeout: int = 75) -> str | None:
        if not prompt.strip():
            return None
        if self.binding_available:
            llm = self._load_in_process()
            if llm is not None:
                try:
                    with self._lock:
                        response = llm.create_chat_completion(
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are RoadLegal. Answer only from supplied sources. /no_think",
                                },
                                {"role": "user", "content": prompt},
                            ],
                            max_tokens=max_tokens,
                            temperature=0.25,
                            top_p=0.8,
                            top_k=20,
                            repeat_penalty=1.12,
                            stop=["<|im_end|>", "<|endoftext|>"],
                        )
                    output = response["choices"][0]["message"]["content"]
                    return self._clean_output(str(output))
                except Exception as exc:
                    self._last_error = f"{type(exc).__name__}: {exc}"
        return self._generate_cli(prompt, max_tokens=max_tokens, timeout=timeout)

    def _ensure_model(self) -> str | None:
        if self.gguf_model and Path(self.gguf_model).exists():
            return self.gguf_model
        self.gguf_model = _find_gguf_model()
        if self.gguf_model or not self.auto_download:
            return self.gguf_model
        try:
            from huggingface_hub import hf_hub_download

            self.gguf_model = hf_hub_download(repo_id=self.model_repo, filename=self.model_file)
        except Exception as exc:
            self._last_error = f"model download failed: {type(exc).__name__}: {exc}"
            return None
        return self.gguf_model

    def _load_in_process(self) -> Any | None:
        if self._llm is not None:
            return self._llm
        model_path = self._ensure_model()
        if not model_path or not self.binding_available:
            return None
        with self._lock:
            if self._llm is not None:
                return self._llm
            started = time.perf_counter()
            try:
                from llama_cpp import Llama

                threads = max(1, int(os.environ.get("ROADLEGAL_LLM_THREADS", str(min(4, os.cpu_count() or 2)))))
                self._llm = Llama(
                    model_path=model_path,
                    n_ctx=int(os.environ.get("ROADLEGAL_LLM_CONTEXT", "1536")),
                    n_batch=int(os.environ.get("ROADLEGAL_LLM_BATCH", "128")),
                    n_threads=threads,
                    n_threads_batch=threads,
                    use_mmap=True,
                    use_mlock=False,
                    verbose=False,
                )
                self._load_seconds = round(time.perf_counter() - started, 3)
                self._last_error = None
            except Exception as exc:
                self._last_error = f"model load failed: {type(exc).__name__}: {exc}"
                self._llm = None
            return self._llm

    def _generate_cli(self, prompt: str, max_tokens: int, timeout: int) -> str | None:
        model_path = self._ensure_model()
        if not self.llama_cli or not model_path:
            return None
        command = [
            self.llama_cli,
            "-m",
            model_path,
            "-p",
            f"{prompt}\n/no_think",
            "-n",
            str(max_tokens),
            "--temp",
            "0.25",
            "--top-p",
            "0.8",
            "--ctx-size",
            "1536",
            "--no-display-prompt",
            "--no-perf",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            self._last_error = f"llama-cli failed: {type(exc).__name__}: {exc}"
            return None
        if result.returncode != 0:
            self._last_error = (result.stderr or f"llama-cli exit {result.returncode}").strip()[-240:]
            return None
        return self._clean_output(result.stdout or "")

    @staticmethod
    def _clean_output(output: str) -> str | None:
        cleaned = re.sub(r"<think>.*?</think>", "", output, flags=re.DOTALL | re.IGNORECASE)
        cleaned = cleaned.replace("/no_think", "").strip()
        return cleaned if len(cleaned) >= 12 else None
