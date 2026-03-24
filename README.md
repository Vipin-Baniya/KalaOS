# KalaOS

KalaOS is an AI-native art platform for creation, streaming, and distribution that preserves artistic intent, credits effort, and prioritizes human dignity over engagement.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
  - [Running with Docker Compose (recommended)](#running-with-docker-compose-recommended)
  - [Running locally without Docker](#running-locally-without-docker)
- [API Reference](#api-reference)
- [Studio UI](#studio-ui)
- [Running the Tests](#running-the-tests)
- [Project Layout](#project-layout)

---

## Overview

KalaOS analyses text-based art (lyrics, poetry, prose) through a multi-phase pipeline:

| Phase | Module | What it does |
|---|---|---|
| 0 / 10 | `ethics.py` | Screens every request through an ethics gate |
| 1 | `pattern_engine`, `art_genome`, `existential` | Pattern analysis, ArtGenome, existential layer |
| 2 | `kalacraft` | Phonetics, stress, meter, linguistic drift |
| 3 | `kalacomposer` | Musical structure, chord & tempo hints |
| 4 | `kalasignal` | Memorability, longevity, emotional resonance |
| 5 | `kalaflow` | Distribution readiness & release metadata |
| 6 | `kalacustody` | Artistic fingerprint, lineage & legacy record |
| 7 | `frontend/` | Browser-based Studio UI (no build step) |
| 8 | `llm_service` | Kala-LLM — unified artist narrative via Ollama |
| 9 | `temporal` | Temporal meaning, ephemeral art, creative ancestry |

---

## Architecture

```
┌─────────────────────────────────────────┐
│            KalaOS Studio UI             │  frontend/  (static HTML/CSS/JS)
└──────────────────┬──────────────────────┘
                   │ HTTP (POST /deep-analysis)
┌──────────────────▼──────────────────────┐
│         FastAPI Backend (Python)        │  backend/
│  ┌─────────────────────────────────┐    │
│  │  kalacore/   (10 modules)       │    │
│  │  services/llm_service.py        │    │
│  └─────────────────────────────────┘    │
└──────────────────┬──────────────────────┘
                   │ HTTP (Ollama REST API)
┌──────────────────▼──────────────────────┐
│        Ollama  (local LLM runtime)      │
└─────────────────────────────────────────┘
```

---

## Getting Started

### Running with Docker Compose (recommended)

> Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine + Compose plugin.

```bash
# Clone the repo
git clone https://github.com/Vipin-Baniya/KalaOS.git
cd KalaOS

# Start the backend + Ollama sidecar
docker compose up --build

# Pull a model (first time only – in a second terminal)
docker exec -it kalaos-ollama ollama pull llama3
```

The API is now available at **http://localhost:8000** and the interactive docs at **http://localhost:8000/docs**.

Open `frontend/index.html` in your browser to use the Studio UI.

---

### Running locally without Docker

**Prerequisites:** Python ≥ 3.11, [Ollama](https://ollama.com) installed and running.

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Pull a model (skip if already done)
ollama pull llama3

# 3. Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is now available at **http://localhost:8000**.

Open `frontend/index.html` directly in your browser (no build step required).

---

## API Reference

All endpoints accept and return JSON. The `text` field is required for every `POST` endpoint.

### `GET /`

Health check.

```json
{ "status": "ok", "service": "KalaOS API" }
```

---

### `POST /deep-analysis` ⭐ primary endpoint

Runs **all phases** in a single call and returns every phase's output plus a unified Kala-LLM narrative.

**Request**

```json
{
  "text": "Your lyrics or poem here",
  "art_domain": "lyrics",
  "artist_name": "Optional artist name",
  "creation_context": "Optional context for the narrative",
  "model": "llama3"
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `text` | `string` | — | Art text to analyse (**required**) |
| `art_domain` | `string` | `"general"` | `lyrics`, `poetry`, `prose`, `script`, `general` |
| `artist_name` | `string` | `null` | Included in the LLM narrative prompt |
| `creation_context` | `string` | `null` | Background provided to the LLM |
| `model` | `string` | `null` | Override the Ollama model (e.g. `"mistral"`) |

**Response** — `DeepAnalysisResponse`

```json
{
  "narrative": "...",
  "art_genome": { ... },
  "analysis": { ... },
  "existential": { ... },
  "craft": { ... },
  "signal": { ... },
  "composition": { ... },
  "flow": { ... },
  "custody": { ... },
  "temporal": { ... }
}
```

---

### `GET /models`

Returns Ollama models available on the local machine.

```json
{ "models": ["llama3", "mistral"] }
```

---

### `POST /analyze-art`

Phase 1 + LLM suggestion pipeline.

```json
{ "text": "..." }
```

---

### `POST /suggest`

Domain-aware improvement suggestions.

```json
{ "text": "...", "art_domain": "lyrics" }
```

---

### `POST /existential`

Phase 1 existential layer + Phase 9 deep features.

```json
{ "text": "..." }
```

---

### `POST /craft`

Phase 2 KalaCraft — phonetics, stress, meter, linguistic drift.

```json
{ "text": "...", "art_domain": "lyrics" }
```

---

### `POST /signal`

Phase 4 KalaSignal — memorability, longevity, emotional resonance.

```json
{ "text": "...", "art_domain": "lyrics" }
```

---

### `POST /compose`

Phase 3 KalaComposer — musical structure, chord & tempo hints.

```json
{ "text": "...", "art_domain": "lyrics", "tempo_bpm": 90 }
```

---

### `POST /flow`

Phase 5 KalaFlow — distribution readiness & release metadata.

```json
{ "text": "...", "art_domain": "lyrics", "artist_name": "..." }
```

---

### `POST /custody`

Phase 6 KalaCustody — artistic fingerprint & legacy record.

```json
{ "text": "...", "art_domain": "lyrics", "artist_name": "...", "collaborators": [] }
```

---

### `POST /temporal`

Phase 9 Temporal intelligence — meaning across time, ephemeral art, creative ancestry.

```json
{ "text": "...", "art_domain": "lyrics" }
```

---

## Studio UI

Open `frontend/index.html` in any modern browser. No build step, no Node.js required.

By default the UI talks to `http://localhost:8000`. To point it at a different backend set the global variable **before** `app.js` loads:

```html
<script>window.KALA_API_BASE = "https://your-backend.example.com";</script>
<script src="app.js"></script>
```

---

## Running the Tests

```bash
cd backend
pip install -r requirements.txt
pytest ../tests/ -v
```

All 392 tests should pass. The test suite covers every endpoint and every kalacore module with unit and integration tests.

---

## Project Layout

```
KalaOS/
├── backend/
│   ├── main.py                  # FastAPI app — all endpoints
│   ├── requirements.txt         # Python dependencies
│   ├── kalacore/
│   │   ├── pattern_engine.py    # Phase 1 – core pattern analysis
│   │   ├── art_genome.py        # Phase 1 – ArtGenome dataclass
│   │   ├── ethics.py            # Phase 0/10 – ethics gate
│   │   ├── existential.py       # Phase 1/9 – existential layer
│   │   ├── kalacraft.py         # Phase 2 – craft tools
│   │   ├── kalasignal.py        # Phase 4 – signal analysis
│   │   ├── kalacomposer.py      # Phase 3 – musical structure
│   │   ├── kalaflow.py          # Phase 5 – distribution
│   │   ├── kalacustody.py       # Phase 6 – custody & legacy
│   │   └── temporal.py          # Phase 9 – temporal intelligence
│   └── services/
│       └── llm_service.py       # Phase 8 – Kala-LLM (Ollama)
├── frontend/
│   ├── index.html               # Studio UI
│   ├── style.css                # Dark-mode design system
│   └── app.js                   # Vanilla ES2020 application logic
├── tests/                       # pytest test suite (392 tests)
├── docker-compose.yml           # One-command startup
└── README.md
```
