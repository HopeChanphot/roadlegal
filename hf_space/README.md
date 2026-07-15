---
title: RoadLegal AI Backend
emoji: 🚦
colorFrom: green
colorTo: red
sdk: gradio
sdk_version: 6.20.0
python_version: "3.12"
app_file: app.py
pinned: false
startup_duration_timeout: 30m
models:
  - Qwen/Qwen3-0.6B
---

# RoadLegal AI Backend

This Space exposes RoadLegal REST and queued Gradio endpoints through Gradio Server mode. It reuses the versioned RoadLegal source and 909-passage RAG corpus from GitHub, then runs guarded `Qwen/Qwen3-0.6B` generation on the quota-free CPU path.
