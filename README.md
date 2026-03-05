# TruthGuard AI 🛡️

**An Agentic AI Research & Fact-Checking System**

Upload documents → Ask questions → Every claim gets verified against your sources **and the live web**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent%20Graph-orange.svg)](https://langchain-ai.github.io/langgraph)

---

## 🏗️ Architecture

```
User Query
    │
    ▼
[Next.js Frontend]  ──POST /api/ask──►  [FastAPI Backend]
                                                │
                        ┌───────────────────────┴───────────────────────┐
                        ▼                                               ▼
                 [RAG Retriever]                          [LangGraph Orchestrator]
                 Hybrid BM25 + TF-IDF + RRF                            │
                        │                  ┌────────────────────────────┼───────────────────────┐
                        │                  ▼                            ▼                       ▼
                        │       [Answer Generator]          [Claim Extractor]         [Fact Checker]
                        │       (Groq LLM grounded          (Atomic factual           (LLM-based NLI
                        │        on retrieved chunks)        claim splitting)           per claim)
                        │                  │                            │                       │
                        │                  └────────────────────────────┴───────────────────────┘
                        │                                               ▼
                        │                                  [Consistency Checker]
                        │                                  (Cross-claim contradictions)
                        │                                               │
                        │                                               ▼
                        │                                   [Web Verifier]  ◄──── DuckDuckGo
                        │                                   (Live web cross-reference)
                        │                                               │
                        └──────────────────────────────────────────────►▼
                                                              [Answer Refiner]
                                                              (Citations + Dual Confidence)
                                                                        │
                                                                        ▼
                                                            Final Verified JSON Response
```

---

## 🤖 7-Node Agent Pipeline

| # | Node | Role |
|---|---|---|
| 1 | `retrieve_context` | Hybrid BM25+TF-IDF+RRF retrieval of top-k chunks from uploaded docs |
| 2 | `generate_answer` | Groq LLM generates a grounded draft answer from retrieved context |
| 3 | `extract_claims` | LLM splits the answer into atomic, independently verifiable claims |
| 4 | `fact_check_claims` | Per-claim NLI via Groq → ENTAILED / CONTRADICTED / NEUTRAL |
| 5 | `check_consistency` | Detects cross-claim contradictions, assigns `hallucination_risk` |
| 6 | `web_verify_claims` | DuckDuckGo web search cross-references each claim against live web results |
| 7 | `refine_answer` | Removes bad claims, adds citations, computes **dual confidence scores** |

---

## 📊 Dual Confidence Scores

Every response includes three confidence metrics:

| Score | Source | Formula |
|---|---|---|
| **📄 Document Confidence** | From your uploaded documents only | `Σ(supported_confidence) / total_claims` |
| **🌐 Web Confidence** | From live web verification | `Σ(web_supported) + 0.3*(inconclusive) / total_claims` |
| **📊 Overall Confidence** | Weighted blend | `0.6 × doc_conf + 0.4 × web_conf` |

---

## 📁 Project Structure

```
TruthGuard AI/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── answer_generator.py      # Groq LLM draft answer
│   │   │   ├── claim_extractor.py       # Atomic claim splitting
│   │   │   ├── fact_checker.py          # LLM-based NLI verification
│   │   │   ├── consistency_checker.py   # Cross-claim contradiction detection
│   │   │   ├── web_verifier.py          # DuckDuckGo web cross-reference
│   │   │   └── answer_refiner.py        # Rewrite with citations + dual confidence
│   │   ├── services/
│   │   │   ├── ingestion_service.py     # PDF/DOCX/PPTX/TXT/MD/CSV chunking
│   │   │   ├── embedding_service.py     # BM25 + TF-IDF + RRF hybrid search
│   │   │   ├── vector_store.py          # In-memory session store
│   │   │   └── web_search_service.py    # DuckDuckGo search (no API key needed)
│   │   ├── core/
│   │   │   ├── config.py                # Environment variables
│   │   │   └── graph.py                 # LangGraph StateGraph orchestration
│   │   └── api/
│   │       └── routes.py                # FastAPI endpoints
│   ├── main.py
│   └── requirements.txt
├── frontend/                            # Next.js App Router
│   ├── app/
│   │   ├── page.tsx                     # Main UI with dual confidence bars
│   │   ├── layout.tsx
│   │   └── globals.css
│   └── components/
│       ├── UploadZone.tsx               # Multi-file drag & drop
│       ├── ClaimTable.tsx               # Claim verdicts + web sources
│       └── ConfidenceBar.tsx            # Animated confidence bar
├── vercel.json
└── .env.example
```

---

## 🚀 Quick Start (Local)

### 1. Prerequisites
- Python 3.9+
- Node.js 18+
- [Groq API key](https://console.groq.com) (free tier: 100k tokens/day)

### 2. Clone & Configure
```bash
git clone <your-repo-url>
cd "TruthGuard AI"

cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 3. Backend Setup
```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r backend/requirements.txt
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# API running at http://localhost:8000
```

### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# UI running at http://localhost:3000
```

### 5. Usage
1. Open `http://localhost:3000`
2. **Upload** one or more documents (PDF, DOCX, PPTX, TXT, MD, CSV)
3. **Ask** a question about the documents
4. Click **Fact-Check →**
5. View the verified answer, per-claim verdicts, web sources, and dual confidence bars

---

## 📦 Supported File Formats

| Format | Extension |
|---|---|
| PDF | `.pdf` |
| Word Document | `.docx`, `.doc` |
| PowerPoint | `.pptx`, `.ppt` |
| Plain Text | `.txt`, `.md` |
| Spreadsheet | `.csv` |
| Other Text | `.json`, `.xml`, `.html` |

Upload **multiple files at once** — all files are indexed in the same session, enabling cross-document queries.

---

## 📡 API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/upload` | POST | Upload one or more files (multipart/form-data) |
| `/api/upload-text` | POST | Upload raw text directly |
| `/api/ask` | POST | Run the full fact-checking pipeline |
| `/api/sessions` | GET | List active sessions |
| `/api/sessions/{id}` | DELETE | Clear a session |

### `POST /api/upload` — Request
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.docx" \
  -F "session_id=my-session"
```

### `POST /api/ask` — Response Schema
```json
{
  "session_id": "abc123",
  "query": "When was Tesla founded?",
  "draft_answer": "Tesla was founded in 2003...",
  "refined_answer": "Tesla was founded in July 2003 [1]...",
  "confidence_score": 0.87,
  "document_confidence": 0.91,
  "web_confidence": 0.80,
  "claims": [
    {
      "claim": "Tesla was founded in 2003.",
      "verdict": "supported",
      "confidence": 0.95,
      "reasoning": "The evidence directly states Tesla was incorporated in July 2003.",
      "evidence": ["Tesla, Inc. was incorporated in July 2003..."],
      "hallucination_risk": "low",
      "cross_contradiction": false,
      "web_verdict": "supported",
      "web_confidence": 0.85,
      "web_reasoning": "Multiple web sources confirm Tesla was founded in 2003.",
      "web_sources": [
        { "title": "Tesla History", "url": "https://...", "snippet": "..." }
      ]
    }
  ],
  "sources": ["tesla_annual_report.pdf"],
  "web_sources": [...],
  "removed_claims": []
}
```

---

## 🌐 Deploy on Vercel / Railway

### Backend (FastAPI) → Railway or Render
```bash
# Railway
railway init && railway up

# Set environment variable:
# GROQ_API_KEY=your_groq_api_key_here
```

### Frontend (Next.js) → Vercel
1. Push to GitHub
2. Import at [vercel.com/new](https://vercel.com/new)
3. Set env var: `NEXT_PUBLIC_API_URL=https://your-backend.railway.app`
4. Deploy

---

## 📊 How Hallucination is Reduced

1. **Retrieval-Grounded Generation** — Answer is generated only from retrieved document chunks, not LLM memory
2. **Claim-Level NLI** — Every factual claim is independently verified against evidence
3. **Web Cross-Reference** — Claims are also checked against live DuckDuckGo search results (no API key needed)
4. **Dual Confidence Scoring** — Separate document vs. web confidence, weighted overall score
5. **Answer Refinement** — Unsupported/contradicted claims are removed or flagged before final output
6. **Cross-Contradiction Detection** — Claims that logically contradict each other are flagged `HIGH RISK`

---

## ⚙️ Configuration

Edit `backend/app/core/config.py` to tune:

| Setting | Default | Description |
|---|---|---|
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model to use |
| `CHUNK_SIZE` | `500` | Characters per document chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between adjacent chunks |
| `TOP_K` | `5` | Number of chunks retrieved per query |

> **Token-saving tip:** Use `llama3-8b-8192` or `mixtral-8x7b-32768` in `config.py` to reduce token usage on the free Groq tier.

---

## 🛡️ Error Handling

| Scenario | Behavior |
|---|---|
| No documents uploaded | Returns error: "Session not found. Please upload documents first." |
| Unsupported file type | Attempts text decoding; raises 422 if no text found |
| Groq rate limit (429) | Error is caught and returned as a clean JSON error message |
| Web search SSL failure | Silently falls back through 3 search backends |
| LLM JSON parsing fails | Falls back to raw text verdict parsing |
| Claim extraction fails | Returns answer with 0 claims (no verification) |

---

## 🔮 V2 Roadmap

- [ ] Streaming verification (live per-claim SSE updates)
- [ ] PDF report export with highlighted claims
- [ ] "Trust score" per paragraph
- [ ] Qdrant Cloud vector DB integration (for persistent sessions)
- [ ] Citation footnotes in refined answer
- [ ] Multi-language document support

---

## 🧠 What This Demonstrates

- ✅ **Agentic workflows** with LangGraph StateGraph (7-node pipeline)
- ✅ **RAG** with hybrid BM25 + TF-IDF + RRF retrieval (no external DB)
- ✅ **LLM-based NLI** for claim verification (more accurate than small HF models)
- ✅ **Web-augmented verification** via DuckDuckGo (no API key needed)
- ✅ **Dual confidence scores** — document vs. web vs. overall
- ✅ **Multi-format ingestion** — PDF, DOCX, PPTX, TXT, MD, CSV
- ✅ **Hallucination detection** at the atomic claim level
- ✅ **Explainable AI** — every verdict has evidence, reasoning, and web sources
- ✅ **Production mindset** — CORS, error handling, session management, graceful degradation

---

Made with ❤️ using **FastAPI · LangGraph · Groq · Next.js · DuckDuckGo**
