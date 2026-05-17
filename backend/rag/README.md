# 🧠 SustainAI V2: Retrieval-Augmented Operational Intelligence

This directory contains the core RAG (Retrieval-Augmented Generation) operational intelligence engine for the **SustainAI V2** multi-agent facility platform.

It completely replaces hardcoded energy assumptions (kW, operating hours, efficiency bounds) with dynamic, grounded specifications semantically retrieved from real-world energy standards and manual PDFs located in the `/RAG` root folder.

---

## 🏗️ ARCHITECTURE & TECH STACK

- **PDF Ingestion Parser**: `pypdf` + intelligent overlapping character chunker.
- **Local Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` generating 384-dimensional dense semantic vectors locally.
- **Local Vector Database**: `FAISS` (Facebook AI Similarity Search) persisted as a memory-mapped local file database.
- **Dynamic Classification**: Maps raw device IDs (e.g. `HVAC_Block_A`, `Lab_PCs`) into domain-specific infrastructure categories.
- **Hybrid Resilience Fallback**: High-fidelity keyword matching over compiled standard specifications triggers automatically if `FAISS` is not yet ingested or package installation is pending, guaranteeing **zero demo crashes**.

---

## 📁 FILES & MODULES

1. **[`retriever.py`](file:///c:/Users/ayush/Desktop/sustainable%20ai/backend/rag/retriever.py)**: Central search query interface exposing semantic retrieval, category-specific context filters, and dynamic specification lookups.
2. **[`ingest.py`](file:///c:/Users/ayush/Desktop/sustainable%20ai/backend/rag/ingest.py)**: Loads, splits, classifies, and indexes all PDFs inside `/RAG`. Extracts rated wattage, standby load, and operating hours dynamically.
3. **[`rag.py`](file:///c:/Users/ayush/Desktop/sustainable%20ai/backend/app/api/rag.py)**: FastAPI router exposing trigger ingestion, semantic query testing, and device spec lookups.

---

## 📐 DYNAMIC ENERGY SAVINGS MODEL

Instead of static fictional constants (like assuming every appliance is exactly `1.5 kW` and runs `4.0 hours`), the Simulator Agent dynamically retrieves the specs:

$$\text{savings\_inr} = \left((\text{typical\_hrs} - \text{proposed\_hrs}) \times \text{rated\_kw} \times 30 \times \text{tariff}\right) + \text{peak\_shift\_savings}$$

*Where `rated_kw` and operating hours are dynamically loaded from retrieved BEE, ECBC, or ASHRAE standards based on device type.*

---

## ⚡ SETUP & RUNNING INSTRUCTIONS

### 1. Install Dependencies
Make sure you have installed the updated dependencies in the workspace:
```bash
pip install -r requirements.txt
```

### 2. Trigger Ingestion (Vector Database Build)
You can trigger local text extraction and FAISS index compilation in two ways:

#### Option A: Via Python Script (Direct)
Run the ingestion script from the workspace root:
```bash
python -m backend.rag.ingest
```

#### Option B: Via REST API
Send an authenticated HTTP POST request to the API:
```bash
curl -X POST http://localhost:8000/api/rag/ingest
```

The database index files will compile into `backend/rag/vector_store/index.faiss`.

### 3. Verify Semantic Search
Query retrieved standards and citations dynamically:
```bash
curl -X GET "http://localhost:8000/api/rag/query?query=HVAC+cooling+efficiency"
```
