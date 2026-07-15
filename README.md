---
title: RoadLegal BIMSTEC
emoji: 🚦
colorFrom: green
colorTo: red
sdk: docker
app_port: 7860
models:
  - Qwen/Qwen3-0.6B-GGUF
preload_from_hub:
  - Qwen/Qwen3-0.6B-GGUF Qwen3-0.6B-Q8_0.gguf
---

# RoadLegal

RoadLegal is an offline-first road-safety and traffic-law chatbot for the BIMSTEC Road Safety Hackathon 2026. It combines jurisdiction-filtered multilingual retrieval, verified fine lookup, geofencing, quizzes, and a cloud or local `llama.cpp` model runtime.

The current build is a runnable MVP designed for demo and extension:

- Local web app with chat, challan calculator, quiz/scenario game content, source citations, feedback, and country/jurisdiction switching.
- Hybrid BM25+ RAG over 909 local passages with Unicode query expansion, source-quality weighting, and strict country isolation.
- Starter BIMSTEC legal/safety seed data plus expanded Thailand road-law/game content and a downloader for official source documents.
- Persistent Qwen3-0.6B GGUF generation through `llama-cpp-python`, with verified model download and answer caching.
- Evidence validation for generated numbers, citations, and high-risk consequences before an AI answer is shown.
- Extractive RAG fallback when no runnable GGUF model is present.

## Detailed Documentation

- [Development, Technical, and Support Guide](docs/DEVELOPMENT_TECHNICAL_SUPPORT_GUIDE.md)
- [Hackathon Submission Notes](docs/HACKATHON_SUBMISSION.md)
- [Cloud AI Deployment](docs/CLOUD_AI_DEPLOYMENT.md)
- [Support](SUPPORT.md)

## Quick Start

```powershell
python -m roadlegal.server --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Public Hosting Options

### Option A: GitHub Pages Static Demo

This is the fastest way for other users to try RoadLegal. It runs fully in the browser using `web/static-data.json`, so no server is required.

1. Create a new GitHub repository.
2. Push this project.
3. In GitHub, open `Settings -> Pages`.
4. Set `Source` to `GitHub Actions`.
5. Push to `main` or `master`.

The workflow in `.github/workflows/pages.yml` deploys the `web/` folder. The static demo supports chat, country switching, challan calculation, quizzes, citations, and Thailand-specific game content.

### Option B: Cloud AI Backend

The primary free AI target is a Hugging Face Docker Space. Add a GitHub Actions secret named `HF_TOKEN`, then run `Deploy AI Backend to Hugging Face Space`. The workflow creates or updates `HopeChanphot/roadlegal`; complete instructions are in [Cloud AI Deployment](docs/CLOUD_AI_DEPLOYMENT.md).

- Hugging Face Spaces: free 2-vCPU/16-GB CPU host for Qwen3-0.6B.
- Render: connect the GitHub repo using `render.yaml`; use an instance with enough memory.
- Railway: connect the repo; `railway.json` and `Dockerfile` are included.
- Any Docker host:

```powershell
docker build -t roadlegal .
docker run -p 8000:8000 roadlegal
```

Cloud services should set `PORT`; the server reads it automatically.

If `python` is not on PATH, use the bundled runtime detected by Codex:

```powershell
& "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m roadlegal.server --host 127.0.0.1 --port 8000
```

## Build or Refresh the RAG Index

The repository includes curated seed passages so it works immediately. To download official source documents when network access is available:

```powershell
python scripts/download_sources.py
python scripts/build_index.py
```

Downloaded files are stored under `data/raw/downloads/`. The processed index is stored at `data/processed/passages.json`.

## Optional Local LLM

RoadLegal defaults to the official Apache-2.0 Qwen3-0.6B Q8 GGUF. Download and verify it with:

```powershell
python scripts/download_model.py
pip install llama-cpp-python==0.3.34 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

To use another model, place a GGUF in `models/` or set:

```powershell
$env:ROADLEGAL_GGUF_MODEL="C:\path\to\model.gguf"
```

The app automatically switches to persistent generative RAG when `llama-cpp-python` can load the GGUF. A compatible `llama-cli` remains a fallback runtime.

## API

- `GET /api/health` - runtime, index, and model status.
- `POST /api/chat` - grounded answer with citations and generation-guard status.
- `GET /api/search?q=...&jurisdiction=...` - retrieval results and diagnostics.
- `POST /api/calculate-challan` - fine lookup by jurisdiction, offence, and vehicle class.
- `GET /api/jurisdictions` - available jurisdictions.
- `GET /api/geofence?lat=...&lon=...` - rough country-level jurisdiction detection.
- `GET /api/quiz?jurisdiction=thailand_national` - country-aware quiz and scenario questions.
- `POST /api/feedback` - local feedback log.

## Legal Accuracy Note

RoadLegal is not legal advice. Fine schedules and enforcement rules change frequently and may vary by state, municipality, vehicle class, road type, and officer/court action. The app is built to cite source material, mark uncertain data clearly, and support a legal-review update pipeline.

## Project Layout

```text
roadlegal/              Python backend and RAG logic
web/                    Static browser app
data/seed/              Curated starter knowledge base
data/raw/downloads/     Downloaded official documents
data/processed/         Built RAG index
scripts/                Download and indexing tools
tests/                  Unit tests
models/                 Optional local GGUF models
```

## GitHub Preparation

Large local models are ignored by `.gitignore`. Commit source code, seed data, and scripts; keep downloaded PDFs optional unless the competition rules allow redistributing them.
