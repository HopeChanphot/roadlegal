# RoadLegal Hackathon Submission Notes

## Problem Fit

RoadLegal targets the DriveLegal problem statement for the BIMSTEC Road Safety Hackathon 2026:

- Location-specific legal guidance through jurisdiction selection and starter geofencing.
- Challan calculator using structured fine data by offence, jurisdiction, and vehicle class.
- Offline robustness through local seed data, downloaded source ingestion, and deterministic extractive RAG.
- Legal accuracy through citations, review flags, source manifests, and cautious answers when fine data is incomplete.
- Behaviour change through safety coaching and gamified quizzes, including Thailand-specific scooter, monsoon, tourist-document, and drink-driving scenarios.

## Current Demo

Run:

```powershell
python -m roadlegal.server --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

For public demos, deploy the static GitHub Pages build. It uses packaged browser-side RAG data and does not need a Python server. For a full backend demo, deploy the repo to Render or Railway using the included `render.yaml`, `railway.json`, `Dockerfile`, and `Procfile`.

Demo queries:

- What is the fine for overspeeding in India for a car?
- Do motorcycle passengers need helmets?
- What happens for drunk driving?
- Give me a cross-border checklist for India to Bangladesh.
- Switch the menu to Thailand, then ask: What are Thailand helmet rules for scooter passengers?
- Switch the menu to Thailand and play the quiz; it now loads Thailand-specific scenarios.

## Local Model Status

Detected on this machine:

- `llama-cli.exe`
- `llama-server.exe`
- cached Hugging Face `Llama-3.2-3B-Instruct` safetensors

The current app runs in extractive RAG mode because `llama.cpp` requires GGUF weights. Put a quantized GGUF model in `models/` or set `ROADLEGAL_GGUF_MODEL` to enable generative RAG.

## RAG Corpus

The downloader successfully fetched:

- WHO road traffic injuries fact sheet
- WHO global status report publication page
- India Motor Vehicles Act, 1988 PDF
- Bangladesh Road Transport Act, 2018 page

The processed index currently contains 658 passages. Thailand now has expanded seed passages and game content. Other BIMSTEC jurisdictions are represented by seed records marked `needs_review` until updated official documents are ingested and reviewed.

## Legal Review Pipeline

1. Add source URLs to `data/seed/source_manifest.json`.
2. Run `scripts/download_sources.py`.
3. Run `scripts/build_index.py`.
4. Update `data/seed/fine_schedule.json` only after verifying the current fine schedule from official government or police notices.
5. Keep `verified=false` for translated, secondary, or stale records until legal review is complete.

## Roadmap

- Add state/municipal polygons for geofencing instead of rough country boxes.
- Add official fine schedules for every BIMSTEC country and major border states/cities.
- Add a GGUF Phi, SmolLM, Gemma, or Llama 3B model for fluent on-device generation.
- Add speech input/output and offline translation packs.
- Add signed legal-data releases and version stamps for auditability.
