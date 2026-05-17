# 🧠 SustainAI V2: Architectural Decision Log (ADR)

> *"Considered X, chose Y, because Z."*  
> This document details the high-fidelity engineering decisions made during the design, refactoring, and scaling of the SustainAI V2 platform. It showcases our architectural thinking, compromise assessments, and alignment with enterprise-grade automation standards.

---

### 📡 Decision 1: Telemetry Simulation Architecture
*   **Considered (X)**: Running the telemetry simulation loops directly inside the Streamlit frontend script using `time.sleep()`.
*   **Chose (Y)**: A persistent background scheduler (`APScheduler`) inside the FastAPI backend, controlled by the frontend via REST POST requests (`/api/telemetry/start`).
*   **Because (Z)**: Streamlit operates on a virtual DOM model that re-runs the entire script on page switching or widget interactions. Any frontend-side loop is instantly terminated during page switching. A backend-side scheduler runs out-of-band and persistently, allowing telemetry to flow continuously even when the operator leaves the simulator page.

---

### 🚨 Decision 2: Evolution from Passive Anomaly Detection to Closed-Loop SCADA
*   **Considered (X)**: A passive `anomaly_node` that simply reports statistical outliers into the database as raw JSON records.
*   **Chose (Y)**: A proactive **Surveillance Agent** at the beginning of the LangGraph pipeline that scans raw telemetry, compiles a detailed "Surveillance Dispatch Report", and passes explicit corrective instructions downstream to the **Recommendation & Doctor Agents** in a closed SCADA loop.
*   **Because (Z)**: Traditional passive analytics fail to drive real-world action. Under Capgemini's "Real-World Automation" theme, we designed a self-healing loop: the Surveillance Agent spots the leak, the Recommendation Agent designs the fix, and the Doctor Agent audits the execution against building profiles to verify optimization.

---

### 🔄 Decision 3: High-Frequency UI Synchronizer & State Buffering
*   **Considered (X)**: Immediately dropping the frontend out of high-frequency (1-second) fast-refresh mode the moment the pipeline returns an "Idle" state.
*   **Chose (Y)**: A **4-second temporal buffer window** inside the frontend dashboard (`1_Dashboard.py`) tracked by `analysis_start_time` when deep analysis is triggered.
*   **Because (Z)**: Because the reasoning pipeline is triggered asynchronously via FastAPI background tasks, there is a 1-2 second execution latency before the worker thread boots and updates the state from `"Idle"` to `"context_node"`. Without this buffer, the frontend would prematurely terminate its fast-refresh cycle before the agents could write their first active logs, locking the UI from updates.

---

### 🧼 Decision 4: Log Duplication & DB Safeguard Pass
*   **Considered (X)**: Blindly appending agent logs (`AgentLog`) to the database on every pipeline run, relying on client-side filtering.
*   **Chose (Y)**: A transactional **Auto-Purge Log-Clearing pass** executed at the very start of both deep analysis and lightweight telemetry ticks.
*   **Because (Z)**: Because sessions are persistent in SQLite, running the pipeline multiple times for the same `session_id` accumulated multiple duplicate agent logs (e.g., three separate Context Agent logs). Purging previous logs associated with the session at the start of a run ensures a pristine, single-run visual trace in the UI and keeps the database clean.

---

### ⚡ Decision 5: LLM Runtime Configuration & Uptime Guardrails
*   **Considered (X)**: Running the Ollama `llama3.2` model locally on the host CPU.
*   **Chose (Y)**: Decoupled Groq LPU Cloud (Llama 3.1 70B/8B) with a highly structured, local deterministic fallback wrapper.
*   **Because (Z)**: CPU-bound local model inference takes 15-30 seconds per agent node, destroying the interactive and visual feel of a live hackathon presentation. Groq LPU cloud completes the entire multi-agent web in under **1.5 seconds**. The local deterministic fallback code ensures the SCADA loop remains 100% stable and operational even if there is internet drop-off during the presentation.

---

### 💬 Decision 6: Streamlit Chat DOM Stability
*   **Considered (X)**: Relying on generic Streamlit widget rendering for the expert chat interface.
*   **Chose (Y)**: Wrapping the chat thread inside a fixed-height scrollable container and assigning explicit unique keys (`key="expert_chat_input"`) to the text widgets.
*   **Because (Z)**: Streamlit's rendering engine suffers from a virtual DOM bug that duplicates inputs and forms during continuous high-frequency screen refreshes. Explicitly assigning static keys completely stabilizes the input field, allowing smooth operator-agent conversation while the screen continues its real-time updates.
