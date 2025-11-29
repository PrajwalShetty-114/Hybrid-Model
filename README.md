<p align="center">
  <h1>🧠🤖 Hybrid Ensemble Intelligence — Ultimate Accuracy Engine</h1>
  
  <p align="center">
    <img alt="python" src="https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white"/>
    <img alt="flask" src="https://img.shields.io/badge/Flask-3.0.0-orange?logo=flask&logoColor=white"/>
    <img alt="render" src="https://img.shields.io/badge/Render-Standard%20Service-007ACC?logo=render"/>
    <img alt="rest" src="https://img.shields.io/badge/REST%20API-JSON-brightgreen"/>
  </p>

  <p align="center">
    <em>Final microservice in the Traffic Flow Prediction pipeline — a Meta-Model that brings consensus and robustness.</em>
  </p>
</p>

---

**🧠 About the Hybrid Model**

- **What it is:** The Hybrid Ensemble Intelligence is a meta-model / orchestrator microservice that collects predictions from multiple specialized models and computes a robust consensus prediction. It does not run heavy ML inference itself — instead it queries and aggregates the outputs of expert sub-model services.
- **Why an ensemble:** Ensemble learning reduces single-model error by combining complementary strengths. This Hybrid engine intentionally leverages:
  - **XGBoost (Precision):** high-fidelity point predictions for edge cases.
  - **Random Forest (Stability):** noise-resistant, consistent performance across distributions.
  - **CatBoost (Context):** strong handling of categorical/contextual features and volume estimation.
- **Role in the pipeline:** Acts as the "Super-Intelligence" to cancel out individual biases and produce a more reliable congestion, speed and volume forecast for traffic flow orchestration and higher-level routing decisions.

**⚙️ How It Works (The Logic Pipeline)**

This section documents the behavior of the `predict()` handler implemented in `app.py`.

- Inbound request: the Hybrid Manager receives a POST JSON payload at `/predict/` and forwards the identical payload to the configured sub-model endpoints defined in `API_URLS`.
- Orchestration flow (actual implementation in `app.py`):
  1. **Sequential Querying of Experts:** The manager iterates through `API_URLS` and posts the same JSON payload to each model URL. Each call uses `requests.post(..., timeout=8)` and collects successful responses. (Note: the current code issues calls in a loop — sequentially — which is simple and robust. See "Next steps" for parallelization suggestions to reduce latency.)
  2. **Aggregation:** For every successful response the manager extracts and stores the model's output votes into three lists: `congestion_votes`, `speed_votes`, and `volume_votes` (where available). A `components` list records which models successfully responded.
  3. **Consensus (Mean):** The final prediction is produced by taking the arithmetic mean of the collected votes (using Python's `statistics.mean`). If no `predictedVolume` is available from any model, volume is set to `0` (safe default). If all sub-models fail to respond, the service returns an error 500.
  4. **Interpretation & Labeling:** The averaged congestion (0–1) is mapped to a human label:
     - <= 0.4 → "Low"
     - > 0.4 → "Moderate"
     - > 0.7 → "High"
     - > 0.9 → "Severe"
  5. **Final JSON:** The response bundles the averaged numeric values and the `components` array (debug/trace info on contributors) and sets `modelUsed` to `Hybrid Ensemble (Average)`.

Key implementation details discovered in `app.py`:
- Timeout for each sub-model call: `timeout=8` seconds.
- Failure behavior: non-200 or exception for any sub-model is logged and excluded from aggregation.
- Final output uses `round()` for numerical readability and includes an `alternativeRoute` placeholder set to `None`.

**🔌 API Documentation**

- **Endpoint**: `POST /predict/`
- **Description**: Forward a payload containing spatial-temporal features to obtain consensus congestion, speed and volume predictions.

Sample request JSON (body):

```json
{
  "coordinates": [13.4050, 52.5200],
  "timestamp": "2025-11-29T08:15:00Z",
  "features": {
    "dayOfWeek": 5,
    "hour": 8,
    "weather": "clear"
  }
}
```

Sample successful response JSON (averaged results):

```json
{
  "predictions": {
    "congestion": { "level": 0.62, "label": "High" },
    "avgSpeed": 42,
    "predictedVolume": 123
  },
  "alternativeRoute": null,
  "components": ["xgboost", "randomforest", "catboost"],
  "modelUsed": "Hybrid Ensemble (Average)"
}
```

- `components`: array of model keys (from `API_URLS`) that contributed to the final average — useful for tracing and debugging.
- Errors: If all sub-models fail, the service returns a 500 with `{ "error": "All sub-models failed to respond" }`.

**🛠️ Setup & Installation**

- Clone the repository:

```bash
git clone https://github.com/PrajwalShetty-114/Hybrid-Model.git
cd Hybrid-Model
```

- Create and activate a virtual environment (Windows / Bash guidance):

```bash
python -m venv venv
# Git Bash / bash on Windows
source venv/Scripts/activate
# If using PowerShell (one-time):
# venv\Scripts\Activate.ps1
# If using cmd.exe:
# venv\Scripts\activate.bat
```

- Install dependencies:

```bash
pip install -r requirements.txt
```

- Important configuration step (CRUCIAL):
  - Edit `app.py` and update the `API_URLS` dictionary so each key points to a reachable sub-model `.../predict/` endpoint. The placeholders in the repository are:

```python
API_URLS = {
    "xgboost": "https://xg-boost-model.onrender.com/predict/",
    "randomforest": "https://randomforestmodel-latest.onrender.com/predict/",
    "catboost": "https://catboost-model.onrender.com/predict/"
}
```

Replace these with your deployed model URLs or local endpoints (including port and `/predict/`). The service will fail to produce results until at least one sub-model responds.

- Run locally:

```bash
python app.py
# or for production-like server use gunicorn
gunicorn app:app --bind 0.0.0.0:8005
```

- Test using `curl` (example):

```bash
curl -X POST http://127.0.0.1:8005/predict/ \
  -H "Content-Type: application/json" \
  -d '{"coordinates": [13.4050, 52.5200], "timestamp":"2025-11-29T08:15:00Z"}'
```

**☁️ Deployment (Render)**

- This is a lightweight Python web service suitable for Render Standard Web Service (no Docker required):
  - Create a new service on Render → choose **Web Service**.
  - Connect your repo and set the start command to:

```
gunicorn app:app --bind 0.0.0.0:$PORT
```

  - Set `ENV` variables if needed and ensure `requirements.txt` contains required packages. Render will use `gunicorn` by default in production mode.

**Operational Notes & Best Practices**

- Observability: Keep `components` and request logs enabled to know which sub-models contributed.
- Timeouts: The call timeout `timeout=8` is a trade-off between waiting for slow models and not blocking clients.
- Robustness: The manager tolerates partial failures; if at least one model responds it will return an averaged prediction.

**Next Steps & Recommended Improvements**

- Parallelization: Convert sequential requests to asynchronous or concurrent requests (e.g., `concurrent.futures.ThreadPoolExecutor` or `asyncio` + `httpx`) to reduce end-to-end latency.
- Retries & Backoff: Add retry logic with exponential backoff for flaky sub-model endpoints.
- Health-checks: Add a `/health` endpoint and optional periodic liveness checks for the sub-models.
- Weighted Ensemble: Replace the simple mean with a weighted average to favor models by historical accuracy.
- Authentication & Rate Limiting: Protect the endpoint and the sub-model endpoints if exposing to public networks.

**Files of Interest**

- `app.py` — the Hybrid Manager implementation (primary file).
- `requirements.txt` — Python dependencies (`Flask`, `gunicorn`, `flask-cors`, `requests`).

---

If you want, I can:
- Implement parallel requests for the three sub-models and test locally.
- Add a `/health` endpoint and a simple retry/backoff wrapper.

Would you like me to implement the parallel-call optimization now? 
