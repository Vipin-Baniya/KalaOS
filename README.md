# KalaOS

KalaOS is an AI-native art platform for creation, streaming, and distribution that preserves artistic intent, credits effort, and prioritizes human dignity over engagement.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
  - [Running with Docker Compose (recommended)](#running-with-docker-compose-recommended)
  - [Running locally without Docker](#running-locally-without-docker)
- [Authentication](#authentication)
- [Themes](#themes)
- [PWA Install](#pwa-install)
- [Capacitor — Native App Builds](#capacitor--native-app-builds)
- [API Reference](#api-reference)
  - [Auth endpoints](#auth-endpoints)
  - [Analysis endpoints](#analysis-endpoints)
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
│            KalaOS Studio UI             │  frontend/  (static HTML/CSS/JS + PWA)
└──────────────────┬──────────────────────┘
                   │ HTTP (POST /deep-analysis, /auth/*)
┌──────────────────▼──────────────────────┐
│         FastAPI Backend (Python)        │  backend/
│  ┌─────────────────────────────────┐    │
│  │  kalacore/   (10 modules)       │    │
│  │  services/llm_service.py        │    │
│  │  services/auth_service.py       │    │
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

# (Optional) create a .env file with a stable signing key and CORS origin
# echo "KALA_SECRET=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env
# echo "KALA_CORS_ORIGINS=http://localhost:5173" >> .env

# Start the backend + Ollama sidecar
docker compose up --build

# Pull a model (first time only – in a second terminal)
docker exec -it kalaos-ollama ollama pull llama3
```

The API is now available at **http://localhost:8000** and the interactive docs at **http://localhost:8000/docs**.

Open `frontend/index.html` in your browser (or serve it with any static file server) to use the Studio UI.

> **Production note:** Set `KALA_SECRET` to a stable random value so session tokens survive server restarts.
> Set `KALA_CORS_ORIGINS` to your frontend's origin (e.g. `https://studio.example.com`) to lock down CORS.

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
KALA_SECRET=my-dev-secret uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is now available at **http://localhost:8000**.

Open `frontend/index.html` directly in your browser (no build step required).

---

## Authentication

KalaOS requires a free account to use the Studio UI.  All `/auth/*` endpoints are provided by `backend/services/auth_service.py`.

| Endpoint | Method | Description |
|---|---|---|
| `/auth/register` | POST | Create a new account (`email`, `password`, `name`) |
| `/auth/login` | POST | Sign in — returns a 30-day signed session token |
| `/auth/forgot-password` | POST | Request a password-reset token (rate-limited: 5/min) |
| `/auth/reset-password` | POST | Apply a new password using the reset token |
| `/auth/me` | GET | Return the current user's public info |
| `/auth/update-profile` | POST | Update the authenticated user's display name |
| `/auth/change-password` | POST | Change password while logged in |

**Security highlights:**
- Passwords hashed with PBKDF2-HMAC-SHA256 (200 000 iterations).
- Session tokens are HMAC-SHA256–signed and carry a 30-day expiry (`exp` field).
- `forgot-password` always returns 200 regardless of whether the email exists (anti-enumeration).
- Login is rate-limited (default 10/min per IP) via [slowapi](https://github.com/laurentS/slowapi).
- Users are stored in SQLite (`kalaos.db`). Path is configurable via `KALA_DB_PATH`.

**Email delivery (optional):**  By default the reset token is returned in the API response (demo mode).  To deliver tokens by email set these environment variables:

```env
KALA_SMTP_HOST=smtp.sendgrid.net
KALA_SMTP_PORT=587
KALA_SMTP_USER=apikey
KALA_SMTP_PASS=your-api-key
KALA_SMTP_FROM=noreply@example.com
KALA_APP_URL=https://studio.example.com
```

When `KALA_SMTP_HOST` is set the token is emailed and **not** included in the API response.

---

## Themes

The Studio UI ships with **6 built-in themes** plus a fully customisable colour override:

| Theme ID | Palette |
|---|---|
| `dark-cosmos` | Deep violet / indigo (default) |
| `ember` | Warm orange / charcoal |
| `ocean` | Teal / deep blue |
| `forest` | Green / dark earth |
| `crimson` | Rose / near-black |
| `light` | Light purple / white |

Themes are stored in `localStorage` and survive page reloads.  If no theme has been manually selected, the UI automatically respects the OS-level `prefers-color-scheme` setting (`light` ↔ `dark-cosmos`).  Custom colour overrides (via the 🎨 panel) are saved separately and persist independently of the active preset.

---

## PWA Install

The Studio UI is a fully installable Progressive Web App.  An "Install KalaOS" banner appears automatically when the browser supports the `beforeinstallprompt` event (Chrome, Edge, and most Android browsers).  On iOS, use **Safari → Share → Add to Home Screen**.

The service worker (`frontend/sw.js`) caches all static assets for offline use.

---

## Capacitor — Native App Builds

`capacitor.config.json` is included at the repo root.  To build iOS / Android / Windows apps:

```bash
# Install Capacitor CLI and platform targets (run once)
npm install @capacitor/core @capacitor/cli @capacitor/ios @capacitor/android

# Sync the frontend web assets into the native projects
npx cap sync

# Open Xcode / Android Studio
npx cap open ios
npx cap open android
```

The `webDir` is set to `frontend/` so no build step is required before syncing.

---

## API Reference

### Auth endpoints

See the [Authentication](#authentication) section above for the full endpoint list.

### Analysis endpoints

All analysis endpoints accept and return JSON. The `text` field is required for every `POST` endpoint.

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

Open `frontend/index.html` in any modern browser, or serve it with a static file server. No build step, no Node.js required.

When you first open the Studio, you are prompted to **sign in or create a free account**.  You can also continue as a guest (no data is persisted for guests).

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

All **422 tests** should pass. The test suite covers every endpoint and every kalacore module with unit and integration tests, including auth registration/login/reset, session expiry, profile updates, and password changes.

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
│       ├── auth_service.py      # Auth – register/login/reset/profile (SQLite)
│       └── llm_service.py       # Phase 8 – Kala-LLM (Ollama)
├── frontend/
│   ├── index.html               # Studio UI (auth overlay + app)
│   ├── style.css                # 6-theme design system + glassmorphism
│   ├── app.js                   # Vanilla ES2020 application logic
│   ├── manifest.json            # PWA manifest
│   └── sw.js                    # Service worker (offline cache)
├── tests/
│   ├── conftest.py              # Shared pytest config (rate limits, DB path)
│   └── ...                      # 422 tests across all modules
├── capacitor.config.json        # Capacitor native app config (iOS/Android/Win)
├── docker-compose.yml           # One-command startup (includes KALA_SECRET)
└── README.md
```
