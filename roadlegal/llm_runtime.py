from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .paths import MODELS_DIR


KNOWN_LLAMA_DIR = Path(r"C:\Program Files\llama-b4907-bin-win-cuda-cu12.4-x64")
KNOWN_HF_LLAMA = Path.home() / ".cache" / "huggingface" / "hub" / "models--meta-llama--Llama-3.2-3B-Instruct"


@dataclass
class ModelStatus:
    mode: str
    llama_cli: str | None
    llama_server: str | None
    gguf_model: str | None
    cached_hf_model: str | None
    note: str


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
        candidates = sorted(MODELS_DIR.glob("*.gguf"), key=lambda p: p.stat().st_size if p.exists() else 0)
        if candidates:
            return str(candidates[-1])
    return None


class LocalLLMRuntime:
    """Optional llama.cpp-backed generator.

    The app remains useful without this runtime because all legal answers are
    grounded in retrieved passages. Generation is enabled only when llama-cli
    and a GGUF model are both present.
    """

    def __init__(self) -> None:
        self.llama_cli = _find_executable("llama-cli")
        self.llama_server = _find_executable("llama-server")
        self.gguf_model = _find_gguf_model()
        self.cached_hf_model = str(KNOWN_HF_LLAMA) if KNOWN_HF_LLAMA.exists() else None

    def status(self) -> ModelStatus:
        if self.llama_cli and self.gguf_model:
            return ModelStatus(
                mode="generative-rag",
                llama_cli=self.llama_cli,
                llama_server=self.llama_server,
                gguf_model=self.gguf_model,
                cached_hf_model=self.cached_hf_model,
                note="GGUF model found; llama-cli generation is available.",
            )
        if self.cached_hf_model:
            note = "Cached Hugging Face weights were found, but llama.cpp requires GGUF for this app."
        elif self.llama_cli:
            note = "llama-cli was found, but no GGUF model was found in models/ or ROADLEGAL_GGUF_MODEL."
        else:
            note = "No local llama.cpp executable or GGUF model found."
        return ModelStatus(
            mode="extractive-rag",
            llama_cli=self.llama_cli,
            llama_server=self.llama_server,
            gguf_model=self.gguf_model,
            cached_hf_model=self.cached_hf_model,
            note=note,
        )

    def generate(self, prompt: str, max_tokens: int = 360, timeout: int = 75) -> str | None:
        if not self.llama_cli or not self.gguf_model:
            return None
        command = [
            self.llama_cli,
            "-m",
            self.gguf_model,
            "-p",
            prompt,
            "-n",
            str(max_tokens),
            "--temp",
            "0.2",
            "--ctx-size",
            "4096",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return None
        output = (result.stdout or "").strip()
        if not output:
            return None
        if prompt in output:
            output = output.split(prompt, 1)[-1].strip()
        return output
