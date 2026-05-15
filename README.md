# SustainAI — AI Sustainability Reasoning Agent

**Team:** Stipend Syndicate  
**Hackathon:** ABB Accelerator Hackathon

---

## Overview

SustainAI is an AI-powered energy intelligence system that uses a multi-agent LangGraph pipeline to analyze energy consumption patterns, detect anomalies, and generate actionable sustainability recommendations.

## Architecture

```
CSV/IoT Data → FastAPI Backend → LangGraph Pipeline → Streamlit Dashboard
                     ↓
                PostgreSQL DB
```

## Quick Start

### 1. Start the database
```bash
docker-compose up -d
```

### 2. Set up environment
```bash
cd backend
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
pip install -r requirements.txt
```

### 3. Start the API
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 4. Generate demo data
```bash
cd datasets
python generate_demo_data.py
```

### 5. Start the dashboard
```bash
cd frontend
streamlit run app.py
```

## Demo Flow

1. Open Dashboard → upload `datasets/demo_scenarios/scenario_late_night_ac.csv`
2. Click **Run AI Analysis** → view AI-generated recommendations
3. Navigate to **Device Insights** → inspect hourly heatmap
4. Open **Simulator** → configure AC parameters → see ₹640 monthly savings
5. Open **Goals** → view before/after improvement chart

## Privacy Approach

- No user PII stored beyond email and name
- All device data associated to user_id only, never exported raw
- API keys stored in .env, never hardcoded
- No third-party analytics or tracking
- Data processed locally — no external data sharing

To delete all data for a user: `DELETE /api/data/delete/{user_id}`

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Uvicorn |
| AI Pipeline | LangGraph + LangChain + GPT-4o-mini |
| Database | PostgreSQL 15 + SQLAlchemy |
| Frontend | Streamlit + Plotly |
| Data | Pandas + NumPy |
