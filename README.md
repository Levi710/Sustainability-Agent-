# SustainAI

AI-powered energy intelligence for building telemetry, anomaly detection, sustainability recommendations, and live IoT-style remediation demos.

## What It Runs

- FastAPI backend with SQLite storage.
- Streamlit dashboard frontend.
- LangGraph multi-agent reasoning pipeline with deterministic fallbacks when API keys are missing or providers fail.
- CSV upload plus live telemetry simulation.

## Quick Start

Use the local virtual environment from the repo root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the API:

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Start the dashboard in a second terminal:

```powershell
.\.venv\Scripts\streamlit.exe run frontend\app.py
```

Then open the Streamlit URL shown in the terminal.

## Demo Flow

1. Open the dashboard and initialize a studio session.
2. Upload `datasets/id_test_data.csv`.
3. Run multi-agent orchestration.
4. Review recommendations, reasoning logs, anomalies, and auditor output.
5. Open Telemetry Simulator to inject live anomaly events and trigger auto-analysis.

## Useful Checks

```powershell
.\.venv\Scripts\python.exe -m compileall backend frontend
$env:PYTHONPATH="backend"; .\.venv\Scripts\python.exe test_pipeline.py
```

## Configuration

- `DATABASE_URL` is optional. By default, the app uses `sustainai.db` at the repo root.
- `SUSTAINAI_API_URL` is optional for the frontend. Default: `http://localhost:8000`.
- `GROQ_API_KEY` or `NVIDIA_API_KEY` enable live LLM calls. Without keys, the deterministic fallback path still produces a demo-safe roadmap.

## Privacy Approach

- API keys live in `.env`.
- Usage data is scoped by generated `session_id`.
- Local SQLite is used by default.
- Delete a session with `DELETE /api/data/{session_id}`.
