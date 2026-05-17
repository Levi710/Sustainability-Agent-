# 🎙️ SustainAI Live Demo Script: The Orchestration Showcase

Use this script to narrate your hackathon presentation while interacting with the SustainAI Studio UI.

---

### 📍 Step 1: Setup & Context (Sidebar)
**Action**: Open the Dashboard. Point to the **Building Profile** section in the sidebar.
**Narrator**: 
> "Welcome to SustainAI. We aren't just looking at charts; we are looking at the digital twin of a building's energy nervous system. Before we start, I’m setting our **Building Profile**. This tells the AI whether it's managing a hospital where life-safety is critical, or a commercial office where comfort is the priority. This establishes our safety guardrails from second zero."

---

### 📍 Step 2: The ID Registry (Upload)
**Action**: Click "Upload CSV" and select `datasets/id_test_data.csv`.
**Narrator**: 
> "I'm uploading a raw IoT telemetry file. Notice these aren't human-readable names—they are Device IDs like `DEV_HVAC_01`. In a standard system, the AI would struggle to understand location. But SustainAI uses a **Registry-Aware Ingestion** pipeline. It instantly maps these IDs to our building's metadata—knowing exactly which floor and which room every sensor belongs to before the AI even starts thinking."

---

### 📍 Step 3: Multi-Agent Orchestration (The Web)
**Action**: Point to the **"MULTI-AGENT ORCHESTRATION"** web as the nodes begin to glow.
**Narrator**: 
> "Now, watch the Orchestration Web. We don't use a single, slow AI model; we use a **Non-Linear Reasoning Web** of specialists:
> * **Layer 1 (Context)**: Locks down safety guardrails.
> * **Layer 2 (Intelligence)**: The Research and Anomaly agents work in parallel to find outliers.
> * **Layer 3 (Analysis)**: Experts determine the specific behavior and draft a surgical fix.
> * This isn't just a pipeline; it's a strategic chain of experts."

---

### 📍 Step 4: The Agent Studio (Under the Hood)
**Action**: Expand the **"🧪 Agent Studio & Prompt Lab"** section. Scroll through the **Trajectory Trace**.
**Narrator**: 
> "For the technical experts in the room, we’ve removed the 'Black Box.' Here in the **Agent Studio**, you can see the **Trajectory Trace**. You can see the raw reasoning output of every agent. If we need to change how an agent thinks—for example, making the Recommendation Agent more aggressive—we can use the **Prompt Lab** to override its logic live, without touching the code."

---

### 📍 Step 5: The Autonomous Fix (Comparison)
**Action**: Toggle the **"🤖 Autonomous Fix Mode"** to **ON**. Point to the **IoT Bridge** logs.
**Narrator**: 
> "Currently, we are in 'Monitor Mode.' But watch what happens when I enable **Autonomous Orchestration**. The system doesn't just suggest a fix—it **dispatches** it. It sends an IoT signal to the hardware, and our **Doctor Agent** follows up to verify the energy drop. We move from 'Observation' to 'Optimization' in real-time."

---

### 📍 Step 6: The Roadmap (Final Results)
**Action**: Scroll down to the **"Sustainability Roadmap"** (Vertical Timeline).
**Narrator**: 
> "Finally, everything is synthesized into this **Roadmap**. It’s a clean, verified timeline of actions taken and savings achieved. We’ve moved from raw, messy data to a fully optimized building strategy in under 30 seconds. SustainAI makes energy efficiency autonomous, auditable, and accessible."

---

### 🏆 Presentation Tips:
* **The "Safety" Question**: If asked about risk, point to the **Doctor Agent**. Explain that every autonomous action is audited by a second AI expert.
* **The "Scale" Question**: Point to the **ID Registry**. Explain that because we use IDs, we can add 1,000 devices to a building and the AI will understand them all instantly.

---

## 🛠️ Technical Appendix: Deep-Dive for Judges

If the judges ask "How does this actually work under the hood?", use these points:

### 1. State Management (LangGraph Orchestration)
* **The Tech**: We use **LangGraph** to build a cyclic state machine. 
* **The Logic**: Instead of a linear prompt, we use a `TypedDict` state. Each agent (node) reads the current state, adds its reasoning, and passes it to the next. This allows for **Check-pointing**—we can resume a reasoning session at any point if the API fails.

### 2. Context Optimization (The Registry)
* **The Tech**: **O(1) Metadata Lookup**.
* **The Logic**: LLMs have limited "context windows." If we send 1,000 lines of descriptive CSV data, the AI gets confused. By using a **JSON Registry**, the backend performs a local lookup and only sends the *relevant* metadata for active devices. This reduces token consumption by ~60% and increases reasoning precision.

### 3. Verification Logic (The Doctor Agent)
* **The Tech**: **Post-Fix Telemetry Comparison**.
* **The Logic**: The Doctor Agent isn't just "chatting." It performs a mathematical comparison. It fetches the `spike_kwh` from the database and compares it against the `live_stream_kwh` after a fix is dispatched. If the consumption doesn't drop within ±20% of the baseline, the Doctor flags the fix as **FAILED** or **SUPERFICIAL**.

### 4. Real-Time Bridge (FastAPI + SSE)
* **The Tech**: **Server-Sent Events (SSE)**.
* **The Logic**: The telemetry simulator streams data to the frontend in real-time. The **IoT Bridge** uses a virtual IP mapping generated from the Device Registry to simulate real hardware handshakes (ACK/NACK signals).

---
*Good luck with the demo! SustainAI is ready for the spotlight.* 🚀🏆
