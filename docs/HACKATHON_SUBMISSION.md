# RoadLegal Hackathon Submission Notes

## Problem Fit

RoadLegal targets the DriveLegal problem statement for the BIMSTEC Road Safety Hackathon 2026:

- Location-specific legal guidance through jurisdiction selection and starter geofencing.
- Challan / ticket calculator using structured fine data by offence, jurisdiction, and vehicle class.
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

Public URL:

```text
https://hopechanphot.github.io/roadlegal/
```

### Recommended Three-Minute Judge Flow

1. Select Thailand in `Offline Demo`, use the helmet prompt, then open `Challan / Ticket` and calculate `Up to THB 2,000` for the prepared two-wheeler case.
2. Change the country menu to Bhutan or Myanmar. Ask the helmet or document question to show that RoadLegal provides a useful complete answer while refusing to invent an exact unreviewed fine.
3. Open `Quiz`, answer a country-specific scenario, and show the teaching feedback, badge progression every 50 points, and restart control resetting the score and level to zero.
4. Open `Directory` and `Feedback` to demonstrate official contacts and the offline update loop.
5. Disconnect the network and reload. The service worker restores the full interface and its 909-passage, 80-topic data bundle; repeat a prepared question and challan/ticket calculation.
6. Reconnect, choose `Live AI`, and ask an open-form question. The Python API runs hybrid retrieval plus Qwen3-0.6B generation, checks citations and numeric claims, and falls back to the prepared pack if cloud compute is unavailable.

The mode switch is deliberately visible. It lets judges distinguish deterministic offline readiness from model-generated live RAG instead of treating an unavailable cloud endpoint as an application failure.

For public demos, GitHub Pages serves the frontend and its packaged offline RAG data. The production frontend calls the public Hugging Face Gradio Space at `https://chanphot-roadlegal.hf.space`, where the Python API, full RAG pipeline, and Qwen3-0.6B run through a queued CPU endpoint without a per-visitor GPU quota. If the API is sleeping or unavailable, the browser keeps the deterministic prepared-answer experience available. Render and Railway remain Docker alternatives.

Demo queries:

- What is the fine for overspeeding in India for a car?
- Do motorcycle passengers need helmets?
- What happens for drunk driving?
- Give me a cross-border checklist for India to Bangladesh.
- Switch the menu to Thailand, then ask: What are Thailand helmet rules for scooter passengers?
- Switch the menu to Thailand and play the quiz; it now loads Thailand-specific scenarios.

## Small Model Status

The completed AI backend uses the official Apache-2.0 `Qwen/Qwen3-0.6B-GGUF` model, file `Qwen3-0.6B-Q8_0.gguf`. The 639 MB artifact is checksum-verified by `scripts/download_model.py` and loaded once per server process through `llama-cpp-python`.

Measured on the development machine, model loading takes about 1.4 seconds. Structured challan answers bypass free-form generation and return in milliseconds; grounded generative answers take about 7-11 seconds when warm and are then cached. If model loading fails, the same API remains usable in deterministic extractive RAG mode.

## RAG Corpus

The downloader successfully fetched official or authoritative material including:

- WHO road traffic injuries fact sheet
- WHO global status report publication page
- WHO 2023 road-safety country profiles for all seven BIMSTEC countries
- India Motor Vehicles Act, 1988 PDF
- Bangladesh Road Transport Act, 2018 page
- Bhutan Road Safety and Transport Act and 2021 Regulations
- Thailand PRD traffic penalties and driver-points notices
- Thailand Department of Land Transport motorcycle safety guidance

The processed index currently contains 909 passages. The browser release adds 80 prepared answer topics across eight country/jurisdiction packs and at least five quiz questions for each. Retrieval is Unicode-aware, expands common road-law terms across BIMSTEC languages, filters strictly by selected jurisdiction, and weights official verified material above translations and unreviewed seeds. Thailand has official fine records plus expanded law and game content. Exact fines that have not completed legal review remain visibly marked `needs_review`.

## Legal Review Pipeline

1. Add source URLs to `data/seed/source_manifest.json`.
2. Run `scripts/download_sources.py`.
3. Run `scripts/build_index.py`.
4. Update `data/seed/fine_schedule.json` only after verifying the current fine schedule from official government or police notices.
5. Keep `verified=false` for translated, secondary, or stale records until legal review is complete.

## Roadmap

- Add state/municipal polygons for geofencing instead of rough country boxes.
- Add official fine schedules for every BIMSTEC country and major border states/cities.
- Evaluate a 3B model or Gemma multimodal variant on larger paid hosts for deeper reasoning and road-sign input.
- Add speech input/output and offline translation packs.
- Add signed legal-data releases and version stamps for auditability.
