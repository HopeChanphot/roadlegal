# RoadLegal

RoadLegal is an offline-first road-safety and traffic-law chatbot for the BIMSTEC Road Safety Hackathon 2026. It combines a local retrieval engine, jurisdiction-aware fine lookup, geofencing, quizzes, and an optional local `llama.cpp` model runtime.

The current build is a runnable MVP designed for demo and extension:

- Local web app with chat, challan calculator, quiz/scenario game content, source citations, feedback, and country/jurisdiction switching.
- Offline RAG over a local knowledge base in `data/processed/passages.json`.
- Starter BIMSTEC legal/safety seed data plus expanded Thailand road-law/game content and a downloader for official source documents.
- Local model detection for the installed `llama-cli` / `llama-server` and any `.gguf` model placed in `models/`.
- Extractive RAG fallback when no runnable GGUF model is present.

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

### Option B: Cloud Backend

Use this when you want the full Python backend and API:

- Render: connect the GitHub repo; `render.yaml` is already included.
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

This machine currently has `llama-cli.exe` and a cached Hugging Face `Llama-3.2-3B-Instruct` snapshot. `llama.cpp` needs GGUF weights, so RoadLegal runs in extractive RAG mode until a `.gguf` model is available.

To enable generation:

1. Place a small instruction GGUF model in `models/`, for example `models/llama-3.2-3b-instruct-q4.gguf`.
2. Or set:

```powershell
$env:ROADLEGAL_GGUF_MODEL="C:\path\to\model.gguf"
```

The app will automatically switch to generative RAG when it can load a GGUF through `llama-cli`.

## API

- `GET /api/health` - runtime, index, and model status.
- `POST /api/chat` - grounded answer with citations.
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
