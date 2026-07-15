# RoadLegal Cloud AI Deployment

## Production shape

RoadLegal uses two cooperating deployments:

- GitHub Pages serves the resilient frontend and packaged static RAG fallback.
- A Hugging Face Docker Space runs the Python API, persistent `llama.cpp` model, hybrid retriever, calculator, quizzes, and feedback endpoint.

The frontend endpoint is configured in `web/config.js`. It currently targets:

```text
https://hopechanphot-roadlegal.hf.space
```

If the API cannot answer within five seconds during startup, the page switches to its local 909-passage static index. A later refresh reconnects after a sleeping Space has awakened.

## Model

- Model: `Qwen/Qwen3-0.6B-GGUF`
- File: `Qwen3-0.6B-Q8_0.gguf`
- Parameters: 0.6 billion
- File size: 639,446,688 bytes
- SHA-256: `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`
- Licence: Apache-2.0
- Runtime: `llama-cpp-python` 0.3.34
- Context: 1,536 tokens
- Batch: 128 tokens
- Output cap: 128 tokens
- Mode: non-thinking, low-temperature grounded synthesis

The Docker image preloads the model from Hugging Face and warms it in a background thread. Common structured fine questions bypass generation and use the verified calculator directly, which reduces latency and avoids model arithmetic errors.

## First deployment

1. Create or sign in to a Hugging Face account. The default workflow expects the username `HopeChanphot`.
2. Create a Hugging Face access token with repository write permission.
3. In `HopeChanphot/roadlegal` on GitHub, open `Settings -> Secrets and variables -> Actions`.
4. Create a repository secret named `HF_TOKEN` containing that token.
5. Open `Actions -> Deploy AI Backend to Hugging Face Space -> Run workflow`.
6. Keep the default Space id `HopeChanphot/roadlegal`, or enter the actual Hugging Face owner and name.
7. Wait for the Docker build and verify `https://hopechanphot-roadlegal.hf.space/api/health`.

The workflow creates the Docker Space if necessary and uploads the application without local models, raw downloads, `.git`, or deliverables. Hugging Face preloads the official model into its cache.

If the Space owner or name changes, update `apiBase` in `web/config.js`, run `scripts/export_static_demo.py`, commit, and push to GitHub.

## Local model test

```powershell
python scripts/download_model.py
pip install llama-cpp-python==0.3.34 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
python -m roadlegal.server --host 127.0.0.1 --port 8000
```

`scripts/download_model.py` verifies both the official byte size and SHA-256 digest before moving the model into `models/`. Model files are excluded from Git.

## Retrieval and safety

The backend uses jurisdiction-filtered BM25+ retrieval rather than asking the LLM to recall laws. It includes Unicode tokenization, BIMSTEC-language offence aliases, title and tag boosts, official-source boosts, unreviewed-source penalties, source diversity, and a 100-answer LRU cache.

Only the selected jurisdiction, BIMSTEC-wide material, and global safety guidance can enter an answer. Delhi additionally inherits India national law. Generated numbers must already occur in the selected evidence, high-risk consequences such as imprisonment or suspension must be present in evidence, and citation ids must map to supplied passages. A failed evidence check returns the deterministic extractive answer.

## Performance profile

Measured on the development computer with the 0.6B Q8 model:

- Retrieval: approximately 1-35 ms across the evaluation set.
- Structured fine answer: approximately 5 ms.
- Model load: approximately 1.3 seconds using memory mapping.
- Grounded generation: approximately 10 seconds cold and 7 seconds warm.
- Repeated cached answer: below 1 ms.

Free cloud CPU performance can differ. Hugging Face CPU Basic currently provides two vCPU and 16 GB RAM and may sleep after inactivity. The first request after sleep can therefore take longer than a warm request.

## Alternative hosts

The same `Dockerfile` works on Railway and paid Render instances. The included `railway.json` uses the Dockerfile. `render.yaml` selects a Docker web service and a non-free instance because a model server is not a good fit for Render's smallest free memory and cold-start behavior.

Set these variables when overriding defaults:

```text
ROADLEGAL_GGUF_MODEL=/path/to/model.gguf
ROADLEGAL_AUTO_DOWNLOAD_MODEL=1
ROADLEGAL_MODEL_REPO=Qwen/Qwen3-0.6B-GGUF
ROADLEGAL_MODEL_FILE=Qwen3-0.6B-Q8_0.gguf
ROADLEGAL_LLM_THREADS=2
ROADLEGAL_LLM_CONTEXT=1536
ROADLEGAL_LLM_BATCH=128
ROADLEGAL_WARM_MODEL=1
ROADLEGAL_CORS_ORIGIN=https://hopechanphot.github.io
```

## Verification

```powershell
python -m unittest discover -s tests
python scripts/evaluate_retrieval.py
python scripts/export_static_demo.py
```

The retrieval evaluator covers India, Thailand in English and Thai, Bhutan, Nepal, Myanmar, and Sri Lanka. It fails if the expected source is absent from the top five or another country's passage leaks into the results.
