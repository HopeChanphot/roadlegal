FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-cloud.txt ./
RUN CMAKE_ARGS="-DGGML_NATIVE=OFF -DGGML_OPENMP=ON" \
    pip install --no-cache-dir \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu \
    -r requirements-cloud.txt

COPY . .

ENV PORT=7860 \
    ROADLEGAL_AUTO_DOWNLOAD_MODEL=1 \
    ROADLEGAL_WARM_MODEL=1 \
    ROADLEGAL_MODEL_REPO=Qwen/Qwen3-0.6B-GGUF \
    ROADLEGAL_MODEL_FILE=Qwen3-0.6B-Q8_0.gguf \
    ROADLEGAL_LLM_CONTEXT=1536 \
    ROADLEGAL_LLM_BATCH=128 \
    PYTHONUNBUFFERED=1

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').environ.get('PORT', '7860') + '/api/health', timeout=4)"

CMD ["sh", "-c", "python -m roadlegal.server --host 0.0.0.0 --port ${PORT}"]
