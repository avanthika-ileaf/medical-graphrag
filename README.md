# Medical GraphRAG System – Consolidated Documentation

This README now contains a full summary of the project's key documentation, merging the previous separate markdown files into a single reference.

---

## 📖 Project Overview

**Medical GraphRAG** is a hybrid medical question‑answering system that combines **graph‑based reasoning** (Neo4j) with **vector‑based semantic search** (Qdrant) to deliver accurate, evidence‑grounded medical insights.

### Core Components
| Component | Purpose |
|-----------|---------|
| **Neo4j** | Stores structured medical knowledge as nodes (patients, drugs, conditions, providers) and relationships (e.g., `TAKES_DRUG`, `HAS_CONDITION`). Enables multi‑hop graph queries. |
| **Qdrant** | Holds semantic embeddings (patients, drugs, conditions, arXiv papers) for similarity search. |
| **Regolo AI** | Provides the LLM (`Llama‑3.3‑70B‑Instruct`) and embedding model (`Qwen3‑Embedding‑8B`). |

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Medical GraphRAG System                   │
├─────────────────────────────────────────────────────────────┤
│  Neo4j (graph) ◄───────► Qdrant (vectors)                     │
│   │                         │                               │
│   │ Nodes & Relationships   │ Vectors & Embeddings           │
│   │ - Patients, Drugs, …   │ - Patient, Drug, Condition …   │
│   ▼                         ▼                               │
│   MedicalGraphRAG (query engine) → LLM (Regolo)            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Workflow

1. **Data Generation** – `scripts/generate_medical_data.py` creates synthetic patients, drugs, conditions, interactions, etc.
2. **Neo4j Population** – `scripts/populate_neo4j_json.py` loads the generated JSON into Neo4j, creating constraints and relationships.
3. **Embedding Generation** – `src/embeddings/embed_pipeline.py` (using `src/embeddings/regolo_embedder.py`) produces 1024‑dimensional embeddings via Regolo and stores them in Qdrant.
4. **Query Execution** – `src/graphrag/medical_graphrag.py` runs a dual‑retrieval pipeline:
   * Graph retrieval via Cypher.
   * Vector retrieval via Qdrant.
   * Fusion of results.
   * Answer generation with the Regolo LLM.

---

## ⚙️ Setup & Quick Start

### Prerequisites
* Docker (for Neo4j & Qdrant)
* Python 3.10+ and the packages listed in `requirements.txt`
* `.env` configured with Regolo API keys and model selections (see **Multi‑Model Configuration** below).

### Docker Services
```bash
docker-compose up -d   # Starts Neo4j and Qdrant containers
```

### Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Run the Full Pipeline
```bash
python -c "from src.embeddings.embed_pipeline import run_all_embeddings; run_all_embeddings()"
```

### Example Query
```python
from src.graphrag.medical_graphrag import MedicalGraphRAG

engine = MedicalGraphRAG()
answer = engine.query("What medications should a patient with diabetes avoid?")
print(answer)
```

---

## 📚 Multi‑Model Regolo Configuration

The project supports multiple Regolo models for different tasks. The default mappings (editable via `.env`) are:

| Task | Default Model |
|------|---------------|
| Primary / Reasoning | `Llama-3.3-70B-Instruct` |
| Fast Tasks / Summarization | `qwen3.5-9b` |
| Medical Analysis | `Llama-3.3-70B-Instruct` |
| Coding | `qwen3-coder-next` |
| Advanced Reasoning | `mistral-small-4-119b` |
| Embeddings | `Qwen3-Embedding-8B` |

You can switch models by editing the corresponding `REGOLO_MODEL_*` variables in `.env`.

---

## 🔧 Embedding Migration (Google Gemini → Regolo)

The project was migrated from Google Gemini embeddings to **Regolo's `Qwen3-Embedding-8B`**:

* **Configuration changes** – `EMBEDDING_MODEL=Qwen3-Embedding-8B`, `EMBEDDING_DIM=1024`.
* **New embedder** – `src/embeddings/regolo_embedder.py` handles batch embedding, retries on rate limits, and provides a context‑manager interface.
* **Updated pipelines** – All embedding scripts now use the Regolo embedder.
* **Dependency update** – Removed `google-generativeai`; added `httpx`.

> **Note:** Existing Qdrant collections created with the old 1536‑dimensional vectors must be recreated (the pipeline does this automatically when run).

---

## 📦 Available Regolo Models

The following models are available from the Regolo API (see `REGOLO_MODELS.md` for the full list):

* `Llama-3.3-70B-Instruct` – High‑quality reasoning (default primary).
* `qwen3.5-9b` – Fast, low‑latency tasks.
* `qwen3-coder-next` – Code analysis/generation.
* `mistral-small-4-119b` – Advanced reasoning.
* `Qwen3-Embedding-8B` – Semantic embeddings (used by the pipeline).
* Plus many others (e.g., `apertus-70b`, `gemma4-31b`, `qwen3.5-122b`).

---

## 🧪 Testing & Validation

Run the connection test to ensure Neo4j and Qdrant are reachable:
```bash
python -m pytest tests/test_connections.py
```

Verify model accessibility:
```bash
python -c "from src.llm.litellm_client import LiteLLMClient; 
print('Fast:', LiteLLMClient.for_fast_tasks().model);
print('Medical:', LiteLLMClient.for_medical().model)"
```

---

## 📂 Repository Structure (Simplified)

```
medical-graphrag/
├─ api/               # FastAPI endpoints (models, routers)
├─ core/              # Config and core services (embeddings, graphrag, llm)
│   ├─ embeddings/
│   ├─ graphrag/
│   └─ llm/
├─ frontend/          # Vite + React UI
├─ infra/              # Docker compose, Neo4j & Qdrant configs
├─ knowledge/          # Data and ontology files
├─ scripts/            # Data generation & import scripts
├─ tests/              # Unit and integration tests
└─ README.md           # (this file)
```

---

## 🗑️ Removed Redundant Markdown Files

The following individual markdown files have been consolidated into this README and removed from the repository:
* `EMBEDDING_MIGRATION.md`
* `EMBEDDING_SWITCH_COMPLETE.md`
* `MULTI_MODEL_USAGE.md`
* `PROJECT_PLAN.md`
* `QUICK_START.md`
* `REGOLO_MODELS.md`
* `summary.md`

---

## 📜 License & Contributions

Please refer to the project's `LICENSE` file for usage terms. Contributions are welcome via pull requests.

---

*End of consolidated documentation.*

**Graph Results**:
- Found 8 patients with diabetes
- Identified Sitagliptin as contraindicated for Type 1 Diabetes
- Found Metformin side effects (lactic acidosis)

**Vector Results**:
- Retrieved 5 semantically similar patients
- Found relevant medical knowledge

**Generated Answer**:
> "Patients with diabetes, particularly those with Type 1 Diabetes, should avoid medications that are contraindicated for their condition or that may exacerbate their symptoms. Specifically, they should avoid Sitagliptin, as it is contraindicated for Type 1 Diabetes [Graph: Drug→Sitagliptin→CONTRAINDICATED_FOR→Type 1 Diabetes]."

**Evidence Provided**:
- Graph paths showing relationships
- Vector similarity scores
- Patient-specific examples

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- Regolo API key (for embeddings and LLM)

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Start containers
docker-compose up -d

# Generate medical data
python scripts/generate_medical_data.py

# Populate Neo4j
python scripts/populate_neo4j_json.py

# Generate embeddings
python src/embeddings/embed_patients.py

# Verify connections
python tests/test_connections.py
```

### Run Queries
```python
from src.graphrag.medical_graphrag import MedicalGraphRAG

m = MedicalGraphRAG()
result = m.query("What medications should a patient with diabetes avoid?")
print(result['answer'])
print(result['graph_hits'])
print(result['vector_hits'])
m.close()
```

## 🔬 Key Features

1. **Hybrid Retrieval**: Combines graph traversal with vector similarity
2. **Evidence Grounding**: Answers include provenance from both graph and vector sources
3. **Multi-Modal Search**: Searches patients, drugs, conditions, and medical literature
4. **Confidence Scoring**: Provides confidence levels for answers
5. **Latency Tracking**: Monitors query performance

## 📝 License

This project is for educational and research purposes.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.
python scripts/load_ontology.py

# Step 3: Populate Neo4j with patients, drugs, conditions
python scripts/populate_neo4j.py

# Step 4: Embed everything into Qdrant
python -c "from src.embeddings.embed_pipeline import run_all_embeddings; run_all_embeddings()"
```

### 4. Run Demo

```bash
# Interactive Streamlit demo
streamlit run demos/interactive_demo.py

# Or run CLI demo queries
python demos/impossible_queries.py
```

## Project Structure

```
medical-graphrag/
├── docker-compose.yml          # Neo4j + Qdrant services
├── .env                        # API keys and config
├── requirements.txt            # Python dependencies
│
├── ontology/
│   └── medical_ontology.owl    # OWL 2.0 ontology (Turtle format)
│
├── data/                       # Generated synthetic data (JSON + CSV)
│
├── scripts/
│   ├── generate_medical_data.py  # Synthesize patients/drugs/conditions
│   ├── load_ontology.py          # Parse OWL → Neo4j schema
│   ├── populate_neo4j.py         # Bulk-load graph data
│   └── import_data.cypher        # Raw Cypher import statements
│
├── src/
│   ├── config.py               # Centralized configuration
│   ├── embeddings/
│   │   ├── embed_pipeline.py   # Collection setup + orchestration
│   │   ├── embed_patients.py   # Patient profile embeddings
│   │   └── embed_knowledge.py  # Drug + condition embeddings
│   └── graphrag/
│       ├── medical_graphrag.py # Top-level MedicalGraphRAG class
│       ├── orchestrator.py     # LangChain agent orchestration
│       ├── fusion.py           # Graph + vector result fusion
│       ├── generator.py        # GPT-4 grounded generation
│       └── retrievers/
│           ├── graph_retriever.py   # Cypher-based graph queries
│           └── vector_retriever.py  # Qdrant semantic search
│
├── evaluation/
│   ├── compare_rag_systems.py  # Standard RAG vs GraphRAG comparison
│   ├── ragas_eval.py           # RAGAS faithfulness evaluation
│   └── benchmark_latency.py   # Latency scaling benchmarks
│
├── demos/
│   ├── impossible_queries.py   # Queries impossible for vector-only RAG
│   └── interactive_demo.py     # Streamlit UI comparison demo
│
└── tests/
    ├── test_connections.py     # Verify Neo4j + Qdrant connectivity
    └── test_semantic_search.py # Verify embedding search works
```

## Key Capabilities

| Capability | Standard RAG | This System |
|------------|-------------|-------------|
| Multi-hop drug interactions | ❌ | ✅ Graph traversal |
| Patient cohort discovery | ❌ | ✅ Cypher pattern match |
| Contraindication checking | ❌ | ✅ CONTRAINDICATED_FOR rel |
| Semantic similarity | ✅ | ✅ Qdrant vectors |
| Explainable citations | ❌ | ✅ Graph path provenance |
| Ontology inference | ❌ | ✅ OWL HighRiskPatient rule |

## Evaluation Results (Expected)

| Metric | Plain LLM | Standard RAG | GraphRAG |
|--------|-----------|-------------|----------|
| Exact Match | ~20% | ~45% | ~75% |
| F1 Score | ~35% | ~60% | ~85% |
| Faithfulness (RAGAS) | ~0.50 | ~0.65 | ~0.92 |
| P95 Latency (1k patients) | N/A | 0.8s | 1.2s |

## Phase Implementation

- **Phase 1**: Docker environment (Neo4j + Qdrant)
- **Phase 2**: OWL ontology design
- **Phase 3**: Neo4j graph population (1000+ patients)
- **Phase 4**: Qdrant vector embeddings
- **Phase 5**: GraphRAG core system (parallel retrieval + fusion)
- **Phase 6**: Demo queries, RAGAS evaluation, Streamlit UI
