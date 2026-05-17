# ⚡ SustainAI V2: Closed-Loop SCADA & Sustainability Multi-Agent Orchestrator

[![Capgemini Hackathon](https://img.shields.io/badge/Capgemini%20Hackathon-Round%202-blue?style=for-the-badge&logo=capgemini)](https://github.com/Levi710/Sustainability-Agent-)
[![Use Case](https://img.shields.io/badge/Use%20Case-46%2F50-green?style=for-the-badge)](https://github.com/Levi710/Sustainability-Agent-)
[![Tech Stack](https://img.shields.io/badge/Tech%20Stack-FastAPI%20%7C%20Streamlit%20%7C%20LangGraph-orange?style=for-the-badge)](https://github.com/Levi710/Sustainability-Agent-)
[![Engine Status](https://img.shields.io/badge/Engine%20Status-Optimal-brightgreen?style=for-the-badge)](https://github.com/Levi710/Sustainability-Agent-)

SustainAI V2 is an enterprise-grade, closed-loop **multi-agent SCADA and energy sustainability orchestrator** designed for smart campuses and commercial buildings. It transforms traditional, passive energy dashboards into an **autonomous, self-healing energy control loop** that active-polls telemetry, designs practical constraints-safe fixes, simulates financial savings, and performs real-time verification audits.

---

## 🏗️ Multi-Agent Orchestration Web

SustainAI V2 replaces generic, static energy recommendations with a compiled non-linear **LangGraph multi-agent reasoning pipeline**.

```
                           ┌────────────────────────┐
                           │      Context Agent     │
                           │   (Profile & Safety)   │
                           └───────────┬────────────┘
                                       │
                ┌──────────────────────┼──────────────────────┐
                ▼                      ▼                      ▼
    ┌──────────────────────┐┌──────────────────────┐┌──────────────────────┐
    │    Research Agent    ││  Surveillance Agent  ││     Pattern Agent    │
    │  (ECBC/BEE Standards)││  (IoT Fleet Poller)  ││   (Occupancy Loops)  │
    └───────────┬──────────┘└──────────┬───────────┘└──────────┬───────────┘
                │                      │                      │
                └──────────────────────┼──────────────────────┘
                                       ▼
                           ┌────────────────────────┐
                           │     Behavior Agent     │
                           │     (Nudge Logic)      │
                           └───────────┬────────────┘
                                       │
                                       ▼
                           ┌────────────────────────┐
                           │      Savings Agent     │
                           │  (High-Fid Simulation) │
                           └───────────┬────────────┘
                                       │
                                       ▼
                           ┌────────────────────────┐
                           │  Recommendation Agent  │
                           │   (IoT Control Sig)    │
                           └───────────┬────────────┘
                                       │
                                       ▼
                           ┌────────────────────────┐
                           │      Doctor Agent      │
                           │   (Audit & Verify)     │
                           └───────────┬────────────┘
                                       │
                                       ▼
                           ┌────────────────────────┐
                           │    Explanation Agent   │
                           │  (Roadmap Synthesis)   │
                           └────────────────────────┘
```

---

## 🎯 Capgemini Hackathon Evaluation Alignment

Every core component of SustainAI V2 has been engineered to perfectly align with Capgemini's **Use Case 46: Sustainability Agent** criteria:

### 1. Savings Estimation Methodology
*   **Dynamic Hardware Simulation**: Evaluates baseline vs peak telemetry usage using real mathematical equations for HVAC, Lighting, and Server Load.
*   **Peak-Tariff Integration**: Computes real-world financial gains in INR (₹) by matching active spikes against peak-hour commercial tariff structures.

### 2. Recommendation Practicality
*   **Constraint-First Safe Whitelisting**: Contextual building profile constraints act as a permanent guardrail. Critical infrastructure (like server room cooling or emergency lighting) is automatically locked out from all optimization actions.

### 3. Behavior Nudges Effectiveness
*   **Automated Twilio SMS Bridge**: If the continuous fleet surveillance polls cross a critical Z-score threshold, the system immediately fires an SMS nudge to the facility manager's phone to prevent prolonged wastage.

### 4. Data Privacy
*   **Isolated Local Session Storage**: All operations are scoped by a unique, cryptographically secure `session_id`. Database logs, audits, and raw usage telemetry are completely isolated inside a zero-shared-state local SQLite database.

### 5. Progress Tracking & Dashboard
*   **Orchestration Web visualizer**: Interactive node-by-node execution graphs showing live active nodes.
*   **IoT Fleet Streamer**: Background polling simulator streaming real-time status updates directly to the frontend.

---

## 🛠️ Technology Stack

*   **LLM Core**: Decoupled Groq LPU Cloud (Llama 3.1 70B/8B) or NVIDIA API Catalog completing full agent runs in **< 1.5 seconds**.
*   **Orchestration**: LangGraph state graph orchestrator.
*   **Backend API**: Python FastAPI Core Service with an APScheduler persistent background telemetry engine.
*   **UI**: Streamlit Premium Dashboard with Plotly and custom SVG/HTML rendering components.
*   **Database**: SQLite + SQLAlchemy ORM.
*   **Secrets**: dotenv configuration pattern (`.env`).

---

## 🚀 Quick Start Guide

### 1. Set Up Environment & Install Dependencies
From the repository root, install the required packages:
```powershell
# Install dependencies
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Configure Environment Variables
Ensure you have a `.env` file at the root with your API keys:
```env
GROQ_API_KEY=your_groq_api_key_here
ENABLE_SMS=False
USE_LOCAL_LLM=False
```

### 3. Launch Backend API (Uvicorn Server)
Start the FastAPI server on port `8000`:
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### 4. Launch Streamlit UI
In a second terminal, start the frontend dashboard on port `8501`:
```powershell
.\.venv\Scripts\streamlit.exe run frontend\app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 📖 Live Demonstration Walkthrough

Follow our step-by-step master presentation script located at:
📄 **[SUSTAINAI_DEMO_SCRIPT.md](file:///c:/Users/ayush/Desktop/sustainable%20ai/SUSTAINAI_DEMO_SCRIPT.md)**

1.  **Initialize**: Open the dashboard and start a new session.
2.  **Upload Data**: Upload our mock high-fidelity telemetry dataset: `datasets/id_test_data.csv`.
3.  **Run Multi-Agent Web**: Watch the interactive **Orchestration Web** light up as agents process data, calculate savings, and audit constraints in real-time.
4.  **Continuous Simulation**: Navigate to the **Telemetry Simulator** to launch persistent background telemetry, inject spikes, and see the self-healing SCADA loop trigger alerts autonomously!
