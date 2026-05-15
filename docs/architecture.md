# SustainAI Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                        │
│  Dashboard | Device Insights | Simulator | Goals            │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP / REST
┌─────────────────────▼───────────────────────────────────────┐
│                    FastAPI Backend                           │
│                                                             │
│  /api/upload/csv   →  CSV ingestion + tariff enrichment     │
│  /api/analyze      →  LangGraph pipeline trigger            │
│  /api/ingest       →  IoT device data                       │
│  /api/recommend    →  Fetch stored recommendations          │
│  /api/anomalies    →  Fetch stored anomalies                │
│  /api/data/delete  →  GDPR-style data deletion              │
└────────────┬────────────────────────┬───────────────────────┘
             │                        │
┌────────────▼──────────┐  ┌─────────▼──────────────────────┐
│   LangGraph Pipeline  │  │       PostgreSQL Database       │
│                       │  │                                 │
│  pattern_node         │  │  users        devices           │
│  anomaly_node         │  │  energy_usage anomalies         │
│  behavior_node (LLM)  │  │  recommendations goals          │
│  savings_node         │  │                                 │
│  recommendation_node  │  └─────────────────────────────────┘
│  explanation_node     │
└───────────────────────┘
```

## Agent Pipeline

Each node in the LangGraph StateGraph processes the shared state sequentially:

1. **pattern_node** — Statistical habit detection (late-night use, peak misuse, idle drain)
2. **anomaly_node** — Z-score based anomaly detection against rolling 7-day baseline
3. **behavior_node** — LLM: Root cause analysis of patterns + anomalies
4. **savings_node** — Simulation of financial impact per behavior
5. **recommendation_node** — LLM: 3 actionable recommendations with savings estimates
6. **explanation_node** — LLM: Human-readable 80-word synthesis

## Data Flow

```
CSV Upload
    │
    ▼
Tariff Zone + Cost Enrichment
    │
    ▼
energy_usage table (PostgreSQL)
    │
    ▼
Baseline Calculation (7-day rolling average by device+hour)
    │
    ▼
LangGraph Pipeline
    │
    ├── Patterns (habit detection)
    ├── Anomalies (z-score flagging)
    ├── Behaviors (LLM root cause)
    ├── Savings Estimates (simulation)
    ├── Recommendations (LLM)
    └── Explanation (LLM synthesis)
         │
         ▼
    DB Storage + API Response + Frontend Display
```

## Tariff Zones (Indian Residential)

| Zone | Hours | Rate (₹/kWh) |
|------|-------|--------------|
| Peak | 6PM–10PM | ₹8.00 |
| Shoulder | 6AM–6PM | ₹5.50 |
| Off-Peak | 10PM–6AM | ₹3.00 |
