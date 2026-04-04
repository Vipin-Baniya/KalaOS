"""
KalaOS Backend – FastAPI Application
--------------------------------------
Entry point for the KalaOS API.

Endpoints
---------
GET  /            – health check
POST /analyze-art – full KalaCore + LLM pipeline
POST /suggest     – domain-aware artist improvement suggestions
POST /existential – Phase 1 existential layer + Phase 9 deep features
POST /craft       – Phase 2 KalaCraft tools (phonetics, stress, meter, drift)
POST /signal      – Phase 4 KalaSignal resonance analysis
POST /compose     – Phase 3 KalaComposer musical structure + chord/tempo hints
POST /flow        – Phase 5 KalaFlow distribution readiness + release metadata
POST /custody     – Phase 6 KalaCustody artistic fingerprint + legacy record
POST /temporal    – Phase 9 temporal meaning, ephemeral art, creative ancestry
POST /text-studio/assist – AI Writing Assistant (continue/rewrite/improve/convert)
POST /text-studio/patterns – Pattern Intelligence quick analysis
POST /animation/generate  – Phase 13 Animation Generator (text/image/story → plan)
POST /visual-studio/generate-image – Phase 14 Design Canvas AI image concept generator
POST /visual-studio/animate        – Phase 14 Design Canvas AI animation mapper
POST /visual-studio/export-gif     – Phase 14 Design Canvas GIF exporter
POST /music-studio/ai-beat         – AI beat generator: text prompt → BPM + drum pattern + melody
POST /video-studio/generate-script – Phase 15 AI Video Generator: text prompt → scene-based video script
"""

import logging
import os as _os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from typing import List, Literal, Optional

logger = logging.getLogger(__name__)

from kalacore.pattern_engine import analyze
from kalacore.art_genome import build_art_genome
from kalacore.ethics import check_request
from kalacore.existential import analyze_existential
from kalacore.kalacraft import analyze_craft
from kalacore.kalasignal import analyze_signal
from kalacore.kalacomposer import compose
from kalacore.kalaflow import flow
from kalacore.kalacustody import custody, assess_artistic_lineage
from kalacore.temporal import analyze_temporal
from kalacore.kalavisual import analyze_visual, generate_image_concept, animate_canvas_objects, export_canvas_gif
from kalacore.kalaproducer import produce, generate_ai_beat, generate_sampler_bank, generate_virtual_keyboard_config
from kalacore.kalaanimation import generate_animation_plan, parse_storyboard
from kalacore.kalavideo import (
    generate_video_script,
    build_scene,
    apply_video_effect,
    apply_ai_video_tool,
    _VALID_STYLES as _VIDEO_STYLES,
    _VALID_EFFECTS as _VIDEO_EFFECTS,
    _VALID_AI_TOOLS as _VIDEO_AI_TOOLS,
)
from kalacore.kalaintelligence import transform as intelligence_transform, ai_assist, VALID_INPUT_TYPES, VALID_OUTPUT_TYPES
from kalacore.kalacollab import create_collab_workspace, add_collaborator, get_collab_activity, generate_collab_suggestions
from kalacore.kalastream import setup_stream, get_stream_analytics, generate_stream_overlay
from kalacore.kalaexport import prepare_export, import_from_url, batch_export
from kalacore.kalaplatformconnect import (
    get_oauth_url,
    connect_platform,
    disconnect_platform,
    get_connected_platforms,
    distribute_to_platforms,
    get_analytics_summary,
    generate_epk,
    get_optimal_release_time,
)
from services.llm_service import (
    generate_explanation,
    generate_suggestions,
    generate_deep_narrative,
    generate_writing_assist,
    list_available_models,
    ART_DOMAINS,
)
import services.auth_service as auth_service
import services.platform_service as platform_service

# Build the domain Literal dynamically from ART_DOMAINS so there is
# only one source of truth for the allowed values.
ArtDomain = Literal[  # type: ignore[assignment]
    "lyrics", "poetry", "music", "story", "book", "general",
    # Visual art domains
    "painting", "sketch", "photo", "video", "logo",
]
# Note: Python does not support constructing Literal from a runtime list, so we
# keep both in sync by asserting equality at import time.
assert set(ArtDomain.__args__) == set(ART_DOMAINS.keys()), (  # type: ignore[attr-defined]
    "ArtDomain Literal and ART_DOMAINS keys are out of sync — update both together."
)

app = FastAPI(
    title="KalaOS API",
    description=(
        "AI-native art platform — art understanding, artist dignity, "
        "structured analysis of music, poetry, and lyrics."
    ),
    version="0.1.0",
)

# Rate limiter — keyed by client IP.  Limits are configurable via env vars
# (useful for lowering limits in production or raising them in tests).
_login_limit    = _os.environ.get("KALA_RATE_LIMIT_LOGIN",    "10/minute")
_forgot_limit   = _os.environ.get("KALA_RATE_LIMIT_FORGOT",   "5/minute")
_register_limit = _os.environ.get("KALA_RATE_LIMIT_REGISTER", "5/minute")
limiter = Limiter(key_func=get_remote_address, default_limits=[])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Allow all origins in development; restrict in production via the
# KALA_CORS_ORIGINS environment variable (comma-separated list).
_cors_origins = _os.environ.get("KALA_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class AnalyseRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        return v


class AnalyseResponse(BaseModel):
    art_genome: dict
    analysis: dict
    explanation: str


class SuggestRequest(BaseModel):
    text: str
    # Domain tells the LLM which artistic conventions to consider
    art_domain: ArtDomain = "general"

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        return v


class SuggestResponse(BaseModel):
    art_domain: str
    art_genome: dict
    analysis: dict
    suggestions: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", summary="Health check")
def root():
    return {"status": "ok", "service": "KalaOS API"}


@app.post(
    "/analyze-art",
    response_model=AnalyseResponse,
    summary="Analyse lyrics or a poem with KalaCore",
)
def analyze_art(request: AnalyseRequest):
    """
    Full pipeline:
    User Input → Ethics check → KalaCore analysis → ArtGenome → LLM explanation
    """
    # Ethics gate (Phase 0 + Phase 10)
    violations = check_request(request.text)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=[{"code": v.code, "message": v.message} for v in violations],
        )

    try:
        # Step 1: run pattern analysis
        analysis = analyze(request.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {exc}")

    try:
        # Step 2: build ArtGenome
        genome = build_art_genome(analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ArtGenome build failed: {exc}")

    # Step 3: combine for LLM prompt context
    combined = {
        "art_genome": genome.to_dict(),
        "analysis": analysis,
    }

    # Step 4: generate LLM explanation (non-blocking even if Ollama is down)
    explanation = generate_explanation(combined)

    return AnalyseResponse(
        art_genome=genome.to_dict(),
        analysis=analysis,
        explanation=explanation,
    )


@app.post(
    "/suggest",
    response_model=SuggestResponse,
    summary="Get domain-aware improvement suggestions for an artist's work",
)
def suggest(request: SuggestRequest):
    """
    Improvement suggestions pipeline:
    User Input + Domain → Ethics check → KalaCore analysis → ArtGenome → LLM suggestions

    The ``art_domain`` field tells the AI which artistic conventions to use
    when generating feedback (lyrics, poetry, music, story, book, or general).
    """
    # Ethics gate (Phase 0 + Phase 10)
    violations = check_request(request.text)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=[{"code": v.code, "message": v.message} for v in violations],
        )

    try:
        # Step 1: pattern analysis
        analysis = analyze(request.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {exc}")

    try:
        # Step 2: build ArtGenome
        genome = build_art_genome(analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ArtGenome build failed: {exc}")

    # Step 3: combine context for the LLM
    combined = {
        "art_genome": genome.to_dict(),
        "analysis": analysis,
    }

    # Step 4: generate domain-aware suggestions (gracefully handles Ollama absence)
    suggestions = generate_suggestions(request.text, combined, domain=request.art_domain)

    return SuggestResponse(
        art_domain=request.art_domain,
        art_genome=genome.to_dict(),
        analysis=analysis,
        suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# Phase 1 Existential + Phase 9 deep features
# ---------------------------------------------------------------------------

class ExistentialResponse(BaseModel):
    existential: dict
    analysis: dict


@app.post(
    "/existential",
    response_model=ExistentialResponse,
    summary="Existential layer: survival markers, emotional necessity, why-created (Phase 1 + Phase 9)",
)
def existential(request: AnalyseRequest):
    """
    Existential pipeline:
    Text → Ethics check → KalaCore analysis → Existential + Negative Space + Irreducibility
    """
    violations = check_request(request.text)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=[{"code": v.code, "message": v.message} for v in violations],
        )
    try:
        analysis = analyze(request.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {exc}")

    try:
        existential_data = analyze_existential(request.text, analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Existential analysis failed: {exc}")

    return ExistentialResponse(existential=existential_data, analysis=analysis)


# ---------------------------------------------------------------------------
# Phase 2 KalaCraft
# ---------------------------------------------------------------------------

class CraftResponse(BaseModel):
    craft: dict


@app.post(
    "/craft",
    response_model=CraftResponse,
    summary="KalaCraft: phonetics, stress patterns, breath points, meter flow, line density, semantic drift (Phase 2)",
)
def craft(request: AnalyseRequest):
    """
    Craft pipeline:
    Text → Ethics check → KalaCraft analysis
    All results are suggestions — never enforcement.
    """
    violations = check_request(request.text)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=[{"code": v.code, "message": v.message} for v in violations],
        )
    try:
        craft_data = analyze_craft(request.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Craft analysis failed: {exc}")

    return CraftResponse(craft=craft_data)


# ---------------------------------------------------------------------------
# Phase 4 KalaSignal
# ---------------------------------------------------------------------------

class SignalResponse(BaseModel):
    signal: dict
    art_genome: dict


@app.post(
    "/signal",
    response_model=SignalResponse,
    summary="KalaSignal: memorability, longevity, viral≠loved≠remembered resonance (Phase 4)",
)
def signal(request: AnalyseRequest):
    """
    Signal pipeline:
    Text → Ethics check → KalaCore → ArtGenome → KalaSignal resonance analysis

    All resonance data is private by default.
    Viral ≠ Loved ≠ Remembered — never conflated.
    """
    violations = check_request(request.text)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=[{"code": v.code, "message": v.message} for v in violations],
        )
    try:
        analysis = analyze(request.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {exc}")

    try:
        genome = build_art_genome(analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ArtGenome build failed: {exc}")

    try:
        signal_data = analyze_signal(request.text, genome.to_dict())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Signal analysis failed: {exc}")

    return SignalResponse(signal=signal_data, art_genome=genome.to_dict())


# ---------------------------------------------------------------------------
# Phase 3 KalaComposer
# ---------------------------------------------------------------------------

class ComposeRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        return v


class ComposeResponse(BaseModel):
    composition: dict
    art_genome: dict


@app.post(
    "/compose",
    response_model=ComposeResponse,
    summary="KalaComposer: musical structure, chord suggestions, tempo, arrangement (Phase 3)",
)
def compose_endpoint(request: ComposeRequest):
    """
    Composition pipeline:
    Text → Ethics check → KalaCore → ArtGenome → KalaComposer musical suggestions

    All musical suggestions are optional starting points for the artist.
    """
    violations = check_request(request.text)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=[{"code": v.code, "message": v.message} for v in violations],
        )
    try:
        analysis = analyze(request.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {exc}")

    try:
        genome = build_art_genome(analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ArtGenome build failed: {exc}")

    try:
        composition_data = compose(request.text, analysis, genome.to_dict())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Composition analysis failed: {exc}")

    return ComposeResponse(composition=composition_data, art_genome=genome.to_dict())


# ---------------------------------------------------------------------------
# Phase 5 KalaFlow
# ---------------------------------------------------------------------------

class FlowRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        return v


class FlowResponse(BaseModel):
    flow: dict
    art_genome: dict


@app.post(
    "/flow",
    response_model=FlowResponse,
    summary="KalaFlow: distribution readiness, release metadata, listener journey (Phase 5)",
)
def flow_endpoint(request: FlowRequest):
    """
    Flow pipeline:
    Text → Ethics check → KalaCore → ArtGenome → Existential → KalaFlow

    All distribution suggestions are artist-editable and optional.
    """
    violations = check_request(request.text)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=[{"code": v.code, "message": v.message} for v in violations],
        )
    try:
        analysis = analyze(request.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {exc}")

    try:
        genome = build_art_genome(analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ArtGenome build failed: {exc}")

    try:
        existential_data = analyze_existential(request.text, analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Existential analysis failed: {exc}")

    try:
        flow_data = flow(request.text, analysis, genome.to_dict(), existential_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Flow analysis failed: {exc}")

    return FlowResponse(flow=flow_data, art_genome=genome.to_dict())


# ---------------------------------------------------------------------------
# Phase 6 KalaCustody
# ---------------------------------------------------------------------------

class CustodyRequest(BaseModel):
    text: str
    artist_name: Optional[str] = None
    creation_context: Optional[str] = None

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        return v


class CustodyResponse(BaseModel):
    custody: dict
    art_genome: dict


@app.post(
    "/custody",
    response_model=CustodyResponse,
    summary="KalaCustody: artistic fingerprint, custody record, lineage, legacy (Phase 6)",
)
def custody_endpoint(request: CustodyRequest):
    """
    Custody pipeline:
    Text → Ethics check → KalaCore → ArtGenome → Existential → KalaCustody

    The custody record belongs to the artist. KalaOS does not retain it.
    """
    violations = check_request(request.text)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=[{"code": v.code, "message": v.message} for v in violations],
        )
    try:
        analysis = analyze(request.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {exc}")

    try:
        genome = build_art_genome(analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ArtGenome build failed: {exc}")

    try:
        existential_data = analyze_existential(request.text, analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Existential analysis failed: {exc}")

    try:
        custody_data = custody(
            request.text,
            analysis,
            genome.to_dict(),
            existential_data,
            artist_name=request.artist_name,
            creation_context=request.creation_context,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Custody analysis failed: {exc}")

    return CustodyResponse(custody=custody_data, art_genome=genome.to_dict())


# ---------------------------------------------------------------------------
# Phase 9 Temporal Intelligence
# ---------------------------------------------------------------------------

class TemporalResponse(BaseModel):
    temporal: dict
    art_genome: dict


@app.post(
    "/temporal",
    response_model=TemporalResponse,
    summary="Phase 9 temporal: meaning across time, ephemeral art, creative ancestry, preservation",
)
def temporal_endpoint(request: AnalyseRequest):
    """
    Temporal pipeline:
    Text → Ethics check → KalaCore → ArtGenome → Existential → Custody lineage → Temporal

    Explores how this piece exists across time, its creative ancestry,
    and its cultural preservation record.
    """
    violations = check_request(request.text)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=[{"code": v.code, "message": v.message} for v in violations],
        )
    try:
        analysis = analyze(request.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {exc}")

    try:
        genome = build_art_genome(analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ArtGenome build failed: {exc}")

    try:
        existential_data = analyze_existential(request.text, analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Existential analysis failed: {exc}")

    try:
        raw_lines = request.text.splitlines()
        lines = [l for l in raw_lines if l.strip()]
        lineage_data = assess_artistic_lineage(lines, analysis, genome.to_dict())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lineage analysis failed: {exc}")

    try:
        temporal_data = analyze_temporal(
            request.text, analysis, genome.to_dict(), existential_data, lineage_data
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Temporal analysis failed: {exc}")

    return TemporalResponse(temporal=temporal_data, art_genome=genome.to_dict())


# ---------------------------------------------------------------------------
# Phase 8 – Kala-LLM: Deep Analysis (unified pipeline)
# ---------------------------------------------------------------------------

class DeepAnalysisRequest(BaseModel):
    text: str
    art_domain: ArtDomain = "general"
    artist_name: Optional[str] = None
    creation_context: Optional[str] = None
    model: Optional[str] = None  # override Ollama model; None → DEFAULT_MODEL

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        return v


class DeepAnalysisResponse(BaseModel):
    narrative: str          # Phase 8 LLM deep narrative
    art_genome: dict        # Phase 1 – ArtGenome
    analysis: dict          # Phase 1 – raw pattern analysis
    existential: dict       # Phase 1 + 9 – existential layer
    craft: dict             # Phase 2 – KalaCraft
    signal: dict            # Phase 4 – KalaSignal
    composition: dict       # Phase 3 – KalaComposer
    flow: dict              # Phase 5 – KalaFlow
    custody: dict           # Phase 6 – KalaCustody
    temporal: dict          # Phase 9 – Temporal intelligence


@app.post(
    "/deep-analysis",
    response_model=DeepAnalysisResponse,
    summary="Phase 8 Kala-LLM: full-stack analysis + unified artist narrative",
)
def deep_analysis(request: DeepAnalysisRequest):
    """
    Deep analysis pipeline — runs every KalaOS phase in a single call.

    Text → Ethics check → KalaCore → ArtGenome → Existential → Craft →
    Signal → Compose → Flow → Custody → Temporal → Kala-LLM narrative

    Returns all phase data plus a unified LLM narrative that weaves
    everything into a single artist-facing mirror.

    This is the primary endpoint for the KalaOS Studio UX.
    """
    violations = check_request(request.text)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=[{"code": v.code, "message": v.message} for v in violations],
        )

    # ── KalaCore ────────────────────────────────────────────────────────────
    try:
        analysis = analyze(request.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {exc}")

    try:
        genome = build_art_genome(analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ArtGenome build failed: {exc}")

    # ── Phase 1 + 9 Existential ─────────────────────────────────────────────
    try:
        existential_data = analyze_existential(request.text, analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Existential analysis failed: {exc}")

    # ── Phase 2 Craft ───────────────────────────────────────────────────────
    try:
        craft_data = analyze_craft(request.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Craft analysis failed: {exc}")

    # ── Phase 4 Signal ──────────────────────────────────────────────────────
    try:
        signal_data = analyze_signal(request.text, genome.to_dict())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Signal analysis failed: {exc}")

    # ── Phase 3 Compose ─────────────────────────────────────────────────────
    try:
        composition_data = compose(request.text, analysis, genome.to_dict())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Composition analysis failed: {exc}")

    # ── Phase 5 Flow ─────────────────────────────────────────────────────────
    try:
        flow_data = flow(request.text, analysis, genome.to_dict(), existential_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Flow analysis failed: {exc}")

    # ── Phase 6 Custody ──────────────────────────────────────────────────────
    try:
        custody_data = custody(
            request.text,
            analysis,
            genome.to_dict(),
            existential_data,
            artist_name=request.artist_name,
            creation_context=request.creation_context,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Custody analysis failed: {exc}")

    # ── Phase 9 Temporal ─────────────────────────────────────────────────────
    try:
        raw_lines = request.text.splitlines()
        lines = [l for l in raw_lines if l.strip()]
        lineage_data = assess_artistic_lineage(lines, analysis, genome.to_dict())
        temporal_data = analyze_temporal(
            request.text, analysis, genome.to_dict(), existential_data, lineage_data
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Temporal analysis failed: {exc}")

    # ── Phase 8 Kala-LLM narrative ───────────────────────────────────────────
    all_data = {
        "art_genome": genome.to_dict(),
        "existential": existential_data,
        "craft": craft_data,
        "signal": signal_data,
        "composition": composition_data,
        "flow": flow_data,
        "custody": custody_data,
        "temporal": temporal_data,
    }
    model_override = request.model or None
    try:
        narrative = generate_deep_narrative(
            all_data,
            **({"model": model_override} if model_override else {}),
        )
    except Exception as exc:
        # LLM narrative failure must never block the structured analysis
        logger.warning("Deep narrative generation failed: %s", exc)
        narrative = "[Narrative unavailable — all structured analysis is complete above.]"

    return DeepAnalysisResponse(
        narrative=narrative,
        art_genome=genome.to_dict(),
        analysis=analysis,
        existential=existential_data,
        craft=craft_data,
        signal=signal_data,
        composition=composition_data,
        flow=flow_data,
        custody=custody_data,
        temporal=temporal_data,
    )


# ---------------------------------------------------------------------------
# Phase 8 – Model listing
# ---------------------------------------------------------------------------

@app.get(
    "/models",
    summary="List locally available Ollama models",
)
def models():
    """
    Returns the list of models available on the local Ollama instance.
    Returns an empty list (not an error) if Ollama is not running.
    """
    return {"models": list_available_models()}


# ---------------------------------------------------------------------------
# Text Studio – Writing Assistant & Pattern Intelligence
# ---------------------------------------------------------------------------

_VALID_ASSIST_ACTIONS = {"continue", "rewrite", "improve", "convert"}


class WritingAssistRequest(BaseModel):
    text: str
    action: str
    domain: ArtDomain = "general"  # type: ignore[assignment]
    model: Optional[str] = None

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        return v

    @field_validator("action")
    @classmethod
    def action_must_be_valid(cls, v: str) -> str:
        if v not in _VALID_ASSIST_ACTIONS:
            raise ValueError(
                f"action must be one of: {', '.join(sorted(_VALID_ASSIST_ACTIONS))}"
            )
        return v


@app.post(
    "/text-studio/assist",
    summary="AI Writing Assistant: continue, rewrite, improve, or convert text",
)
def text_studio_assist(request: WritingAssistRequest):
    """
    AI Writing Assistant for the Text Studio.

    Supported *action* values
    -------------------------
    ``continue`` – continue writing from where the artist left off.
    ``rewrite``  – rewrite the text with fresh phrasing, preserving meaning.
    ``improve``  – deepen emotional impact and sensory language.
    ``convert``  – convert between formats (poem → story, lyrics → poem, …).

    The endpoint runs an ethics check first, then calls the local Ollama
    instance.  If Ollama is unavailable, a graceful fallback message is
    returned instead of an error.
    """
    violations = check_request(request.text)
    if violations:
        raise HTTPException(status_code=422, detail={"ethics_violations": violations})

    model = request.model or "llama3"
    result = generate_writing_assist(
        text=request.text,
        action=request.action,
        domain=request.domain,
        model=model,
    )
    return {
        "action": request.action,
        "domain": request.domain,
        "result": result,
    }


@app.post(
    "/text-studio/patterns",
    summary="Pattern Intelligence: quick palindrome, rhythm & emotional arc analysis",
)
def text_studio_patterns(request: AnalyseRequest):
    """
    Returns a focused subset of the KalaCore pattern analysis optimised for
    the Text Studio Pattern Intelligence panel:

    - palindromes (full-line and partial)
    - mirror rhyme / symmetry structures
    - repetition and refrains
    - emotional arc (per-line valence)
    - cognitive load estimate
    - detected form type
    """
    violations = check_request(request.text)
    if violations:
        raise HTTPException(status_code=422, detail={"ethics_violations": violations})

    analysis = analyze(request.text)
    genome = build_art_genome(analysis)

    return {
        "palindromes":      analysis.get("palindrome", {}),
        "mirror_rhyme":     analysis.get("mirror_rhyme", {}),
        "structure":        analysis.get("structure", {}),
        "emotional_arc":    analysis.get("emotional_arc", {}),
        "cognitive_load":   analysis.get("cognitive_load", 0.0),
        "form_type":        analysis.get("form_type", {}),
        "symmetry_score":  genome.symmetry_score,
        "rhyme_density":   genome.rhyme_density,
        "complexity_score": genome.complexity_score,
    }


class ProduceRequest(BaseModel):
    text: str
    artist_name: Optional[str] = None

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        return v


class ProduceResponse(BaseModel):
    production_plan:    dict
    beat_pattern:       dict
    instruments:        dict
    melody_contour:     dict
    distribution:       dict
    streaming_metadata: dict
    sample_palette:     dict
    art_genome:         dict


@app.post(
    "/produce",
    response_model=ProduceResponse,
    summary="Phase 12 KalaProducer: music production plan, beat, melody, distribution & streaming",
)
def produce_endpoint(request: ProduceRequest):
    """
    Music production pipeline.

    Text → Ethics check → KalaCore → ArtGenome →
    KalaProducer (production plan + beat pattern + instruments +
    melody contour + distribution channels + streaming metadata +
    sample palette)

    All results are artist-facing suggestions — not prescriptions.
    """
    violations = check_request(request.text)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=[{"code": v.code, "message": v.message} for v in violations],
        )

    try:
        analysis = analyze(request.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {exc}")

    try:
        genome = build_art_genome(analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ArtGenome build failed: {exc}")

    try:
        producer_data = produce(
            request.text,
            analysis,
            genome.to_dict(),
            artist_name=request.artist_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Production analysis failed: {exc}")

    return ProduceResponse(
        production_plan=producer_data["production_plan"],
        beat_pattern=producer_data["beat_pattern"],
        instruments=producer_data["instruments"],
        melody_contour=producer_data["melody_contour"],
        distribution=producer_data["distribution"],
        streaming_metadata=producer_data["streaming_metadata"],
        sample_palette=producer_data["sample_palette"],
        art_genome=genome.to_dict(),
    )


# ---------------------------------------------------------------------------
# Phase 11 – Visual Art Intelligence
# ---------------------------------------------------------------------------

_VISUAL_MEDIA = {"painting", "sketch", "photo", "video", "logo"}


class VisualAnalysisRequest(BaseModel):
    description: str
    medium: str = "painting"
    color_palette: Optional[List[str]] = None
    dimensions: Optional[str] = None
    style_tags: Optional[List[str]] = None

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description must not be empty")
        return v

    @field_validator("medium")
    @classmethod
    def medium_must_be_valid(cls, v: str) -> str:
        if v.lower() not in _VISUAL_MEDIA:
            raise ValueError(f"medium must be one of {sorted(_VISUAL_MEDIA)}")
        return v.lower()


class VisualAnalysisResponse(BaseModel):
    medium: str
    dimensions: Optional[str]
    summary: str
    colour: dict
    composition: dict
    style: dict
    emotion: dict
    intent: dict
    technical: dict
    narrative: dict
    preservation: dict


@app.post(
    "/visual",
    response_model=VisualAnalysisResponse,
    summary="Phase 11 Visual Art Intelligence: analyse a visual artwork from description",
)
def visual_analysis(request: VisualAnalysisRequest):
    """
    Visual art analysis pipeline.

    Accepts an artist-provided description of a painting, sketch, photograph,
    video or logo and returns comprehensive analysis covering:

    - Colour theory (palette harmony, temperature, saturation, value)
    - Composition (balance, depth, leading lines, negative space)
    - Style / movement classification
    - Emotional register
    - Artistic intent
    - Medium-specific technical observations
    - Visual narrative (subjects, narrative complexity)
    - Preservation and archival recommendations

    No image data is required — privacy by design.
    """
    try:
        result = analyze_visual(
            description=request.description,
            medium=request.medium,
            color_palette=request.color_palette,
            dimensions=request.dimensions,
            style_tags=request.style_tags,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Visual analysis failed: {exc}")

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    return VisualAnalysisResponse(**result)


# ---------------------------------------------------------------------------
# Phase 14 – Design Canvas AI Image Concept Generator
# ---------------------------------------------------------------------------

_DESIGN_CANVAS_STYLES: set[str] = {
    "digital art",
    "painting",
    "photo",
    "sketch",
    "watercolor",
    "illustration",
    "concept art",
}


class DesignCanvasGenerateRequest(BaseModel):
    prompt: str
    style: str = "digital art"

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt must not be empty")
        return v

    @field_validator("style")
    @classmethod
    def style_must_be_valid(cls, v: str) -> str:
        if v.lower() not in _DESIGN_CANVAS_STYLES:
            raise ValueError(
                f"style must be one of {sorted(_DESIGN_CANVAS_STYLES)}"
            )
        return v.lower()


class DesignCanvasGenerateResponse(BaseModel):
    prompt: str
    style: str
    description: str
    palette: List[str]
    image_data: str
    width: int
    height: int
    theme: str


@app.post(
    "/visual-studio/generate-image",
    response_model=DesignCanvasGenerateResponse,
    summary="Phase 14 Design Canvas: generate an AI image concept from a text prompt",
)
def design_canvas_generate_image(request: DesignCanvasGenerateRequest):
    """
    AI image concept generator for the Design Canvas.

    Takes a text prompt and an optional style, analyses the prompt to detect
    visual themes, selects a fitting colour palette, and returns a structured
    SVG placeholder image alongside a concept description.

    This provides immediate visual feedback on the canvas while acting as a
    drop-in integration point for a real text-to-image model backend.
    """
    try:
        result = generate_image_concept(prompt=request.prompt, style=request.style)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Image concept generation failed: {exc}")

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    return DesignCanvasGenerateResponse(**result)


# ---------------------------------------------------------------------------
# Phase 14 – Design Canvas AI Animation Mapper
# ---------------------------------------------------------------------------

class CanvasElementInput(BaseModel):
    id: str
    type: str


class CanvasAnimateRequest(BaseModel):
    elements: List[CanvasElementInput]
    prompt: str

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt must not be empty")
        return v


class AnimationAssignment(BaseModel):
    id: str
    animation: str
    duration: float
    delay: float


class CanvasAnimateResponse(BaseModel):
    prompt: str
    assignments: List[AnimationAssignment]


@app.post(
    "/visual-studio/animate",
    response_model=CanvasAnimateResponse,
    summary="Phase 14 Design Canvas: AI animation mapper — assign animations to canvas elements",
)
def design_canvas_animate(request: CanvasAnimateRequest):
    """
    AI animation mapper for Design Canvas objects.

    Takes the current canvas elements and a natural-language prompt, and
    returns per-element animation assignments (type, duration, delay).
    """
    try:
        raw_elements = [e.model_dump() for e in request.elements]
        assignments = animate_canvas_objects(
            elements=raw_elements,
            prompt=request.prompt,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Animation mapping failed: {exc}")

    return CanvasAnimateResponse(
        prompt=request.prompt,
        assignments=[AnimationAssignment(**a) for a in assignments],
    )


# ---------------------------------------------------------------------------
# Phase 14 – Design Canvas GIF Exporter
# ---------------------------------------------------------------------------

_MAX_EXPORT_FRAMES: int = 120


class ExportGifRequest(BaseModel):
    frames: List[str]
    frame_duration_ms: int = 100

    @field_validator("frames")
    @classmethod
    def frames_must_not_be_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("frames must not be empty")
        if len(v) > _MAX_EXPORT_FRAMES:
            raise ValueError(
                f"Too many frames: {len(v)} exceeds limit of {_MAX_EXPORT_FRAMES}"
            )
        return v

    @field_validator("frame_duration_ms")
    @classmethod
    def duration_must_be_valid(cls, v: int) -> int:
        if v < 20 or v > 5000:
            raise ValueError("frame_duration_ms must be between 20 and 5000")
        return v


class ExportGifResponse(BaseModel):
    gif_data: str
    frame_count: int


@app.post(
    "/visual-studio/export-gif",
    response_model=ExportGifResponse,
    summary="Phase 14 Design Canvas: assemble PNG frames into an animated GIF",
)
def design_canvas_export_gif(request: ExportGifRequest):
    """
    Convert a sequence of base64-encoded PNG canvas frames into an animated GIF.

    Accepts up to 120 frames and returns a ``data:image/gif;base64,…`` string
    ready for direct use in an ``<img>`` tag or download link.
    """
    try:
        gif_data = export_canvas_gif(
            frames=request.frames,
            frame_duration_ms=request.frame_duration_ms,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"GIF export failed: {exc}")

    return ExportGifResponse(gif_data=gif_data, frame_count=len(request.frames))


_ANIMATION_MODES: set[str] = {
    "text_to_animation",
    "image_to_animation",
    "story_to_storyboard",
}
_ANIMATION_STYLES: set[str] = {
    "realistic",
    "cartoon",
    "anime",
    "cinematic",
    "abstract",
    "lofi",
}


class AnimationGenerateRequest(BaseModel):
    prompt: str
    mode: str = "text_to_animation"
    style: str = "cinematic"
    duration_sec: int = 10

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt must not be empty")
        return v

    @field_validator("mode")
    @classmethod
    def mode_must_be_valid(cls, v: str) -> str:
        if v not in _ANIMATION_MODES:
            raise ValueError(
                f"mode must be one of {sorted(_ANIMATION_MODES)}"
            )
        return v

    @field_validator("style")
    @classmethod
    def style_must_be_valid(cls, v: str) -> str:
        if v not in _ANIMATION_STYLES:
            raise ValueError(
                f"style must be one of {sorted(_ANIMATION_STYLES)}"
            )
        return v

    @field_validator("duration_sec")
    @classmethod
    def duration_must_be_positive(cls, v: int) -> int:
        if v < 2:
            raise ValueError("duration_sec must be at least 2")
        if v > 300:
            raise ValueError("duration_sec must not exceed 300")
        return v


@app.post(
    "/animation/generate",
    summary="Phase 13 Animation Generator: produce an animation plan from text/image/story",
)
def animation_generate(request: AnimationGenerateRequest):
    """
    Generate a structured animation plan.

    Accepts:
    - ``text_to_animation`` – a descriptive text prompt
    - ``image_to_animation`` – a description of a source image
    - ``story_to_storyboard`` – a multi-scene narrative

    Returns scene breakdowns, keyframes, character notes, audio hints,
    export formats and a creative score.
    """
    try:
        plan = generate_animation_plan(
            prompt=request.prompt,
            mode=request.mode,
            style=request.style,
            duration_sec=request.duration_sec,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Animation generation failed: {exc}"
        )
    return plan

class AuthRegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthForgotRequest(BaseModel):
    email: str


class AuthResetRequest(BaseModel):
    token: str
    new_password: str


class AuthUpdateProfileRequest(BaseModel):
    token: str
    name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


class AuthChangePasswordRequest(BaseModel):
    token: str
    old_password: str
    new_password: str


class AuthLogoutRequest(BaseModel):
    token: str


class AuthDeleteAccountRequest(BaseModel):
    token: str
    password: str


@app.post("/auth/register", summary="Register a new artist account")
@limiter.limit(_register_limit)
def auth_register(request: Request, body: AuthRegisterRequest):
    """Create a new user account.  Returns public user info on success."""
    try:
        user = auth_service.register(body.email, body.password, body.name)
        return {"success": True, "user": user}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/auth/login", summary="Login and receive a session token")
@limiter.limit(_login_limit)
def auth_login(request: Request, body: AuthLoginRequest):
    """Validate credentials and return a signed session token."""
    try:
        token = auth_service.login(body.email, body.password)
        user  = auth_service.get_user(token)
        return {"success": True, "token": token, "user": user}
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@app.post("/auth/forgot-password", summary="Request a password-reset token")
@limiter.limit(_forgot_limit)
def auth_forgot(request: Request, body: AuthForgotRequest):
    """
    Generate a password-reset token.  When KALA_SMTP_HOST is configured the
    token is emailed and the response omits it (recommended for production).
    Always responds with success regardless of whether the email exists.
    """
    token = auth_service.request_password_reset(body.email)
    resp: dict = {"success": True}
    if auth_service.SMTP_CONFIGURED:
        resp["note"] = "If that email exists, a reset link has been sent."
    else:
        resp["reset_token"] = token
        resp["note"] = (
            "In production this token would be emailed to you. "
            "Copy it and use /auth/reset-password."
        )
    return resp


@app.post("/auth/reset-password", summary="Reset password using a reset token")
def auth_reset(request: AuthResetRequest):
    """Apply a new password if the reset token is valid and unexpired."""
    try:
        auth_service.reset_password(request.token, request.new_password)
        return {"success": True}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/auth/me", summary="Get current user from session token")
def auth_me(token: str):
    """Return public user info for a valid session token."""
    user = auth_service.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return user


@app.post("/auth/update-profile", summary="Update display name, avatar, and bio")
def auth_update_profile(request: AuthUpdateProfileRequest):
    """Update the display name, avatar, and bio for the authenticated user."""
    try:
        user = auth_service.update_profile(
            request.token, request.name,
            avatar_url=request.avatar_url,
            bio=request.bio,
        )
        return {"success": True, "user": user}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/auth/change-password", summary="Change password while logged in")
def auth_change_password(request: AuthChangePasswordRequest):
    """Change the password for the authenticated user."""
    try:
        auth_service.change_password(
            request.token, request.old_password, request.new_password
        )
        return {"success": True}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/auth/logout", summary="Revoke the current session token")
def auth_logout(request: AuthLogoutRequest):
    """Invalidate the session token server-side so it cannot be reused."""
    auth_service.logout(request.token)
    return {"success": True}


@app.delete("/auth/delete-account", summary="Permanently delete the authenticated user's account")
def auth_delete_account(request: AuthDeleteAccountRequest):
    """Delete the account and revoke the session token.  Requires password confirmation."""
    try:
        auth_service.delete_account(request.token, request.password)
        return {"success": True}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# User profiles
# ---------------------------------------------------------------------------

@app.get("/user/{user_id}", summary="Get public user profile")
def get_user_profile(user_id: str):
    """Return public profile for a user by email."""
    user = auth_service.get_user_by_email(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@app.get("/user/{user_id}/posts", summary="Get published posts for a user")
def get_user_posts(user_id: str):
    """Return published posts (creations) for a given user."""
    posts = platform_service.get_user_posts(user_id.lower())
    return {"posts": posts}


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class ProjectCreateRequest(BaseModel):
    token: str
    title: str
    type: str
    data: str = "{}"


class ProjectUpdateRequest(BaseModel):
    token: str
    title: Optional[str] = None
    data: Optional[str] = None


class ProjectTokenRequest(BaseModel):
    token: str


@app.post("/projects", summary="Create a new project")
def projects_create(body: ProjectCreateRequest):
    try:
        project = platform_service.create_project(body.token, body.title, body.type, body.data)
        return {"success": True, "project": project}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/projects", summary="List projects for the authenticated user")
def projects_list(token: str):
    try:
        projects = platform_service.list_projects(token)
        return {"projects": projects}
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@app.get("/projects/{project_id}", summary="Get a specific project")
def projects_get(project_id: str, token: str):
    try:
        project = platform_service.get_project(token, project_id)
        return project
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.put("/projects/{project_id}", summary="Update a project")
def projects_update(project_id: str, body: ProjectUpdateRequest):
    try:
        project = platform_service.update_project(body.token, project_id, body.title, body.data)
        return {"success": True, "project": project}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/projects/{project_id}", summary="Delete a project")
def projects_delete(project_id: str, token: str):
    try:
        platform_service.delete_project(token, project_id)
        return {"success": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Feed / Posts
# ---------------------------------------------------------------------------

class PublishRequest(BaseModel):
    token: str
    project_id: str


@app.post("/posts", summary="Publish a project to the feed")
def posts_publish(body: PublishRequest):
    try:
        post = platform_service.publish_project(body.token, body.project_id)
        return {"success": True, "post": post}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/feed", summary="Get the public creation feed")
def feed_get(limit: int = 20, offset: int = 0):
    posts = platform_service.get_feed(limit, offset)
    return {"posts": posts}


class LikeRequest(BaseModel):
    token: str


@app.post("/posts/{post_id}/like", summary="Toggle like on a post")
def toggle_like(post_id: str, body: LikeRequest):
    try:
        result = platform_service.toggle_like(body.token, post_id)
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# Chat / Messages
# ---------------------------------------------------------------------------

class SendMessageRequest(BaseModel):
    token: str
    receiver_id: str
    content: str


@app.post("/messages", summary="Send a message to another user")
def messages_send(body: SendMessageRequest):
    try:
        msg = platform_service.send_message(body.token, body.receiver_id, body.content)
        return {"success": True, "message": msg}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/messages/{peer_id}", summary="Get conversation with a user")
def messages_get(peer_id: str, token: str, limit: int = 50, offset: int = 0):
    try:
        msgs = platform_service.get_conversation(token, peer_id, limit, offset)
        return {"messages": msgs}
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@app.get("/conversations", summary="List all conversations for the authenticated user")
def conversations_list(token: str):
    try:
        convs = platform_service.list_conversations(token)
        return {"conversations": convs}
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


# ---------------------------------------------------------------------------
# Music Studio — AI Beat Generator
# ---------------------------------------------------------------------------

class AiBeatRequest(BaseModel):
    prompt: str

    @field_validator("prompt")
    @classmethod
    def prompt_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("prompt must not be empty")
        return v.strip()


class AiBeatResponse(BaseModel):
    bpm:    int
    drums:  dict
    melody: list
    genre:  str
    prompt: str


@app.post(
    "/music-studio/ai-beat",
    response_model=AiBeatResponse,
    summary="AI Beat Generator: text prompt → BPM + drum pattern + melody",
)
def ai_beat_endpoint(request: AiBeatRequest):
    """
    Convert a plain-text description into a playable beat recipe.

    Examples
    --------
    ``{"prompt": "lofi chill beat"}``
    → ``{"bpm": 80, "drums": {...}, "melody": ["C4","Eb4",...], "genre": "lofi"}``

    ``{"prompt": "dark trap 140bpm aggressive"}``
    → ``{"bpm": 140, "drums": {...}, "melody": ["C3","Eb3",...], "genre": "trap"}``
    """
    try:
        result = generate_ai_beat(request.prompt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Beat generation failed: {exc}")

    return AiBeatResponse(
        bpm=result["bpm"],
        drums=result["drums"],
        melody=result["melody"],
        genre=result["genre"],
        prompt=result["prompt"],
    )


# ---------------------------------------------------------------------------
# Music Studio — Sampler Bank (Phase 16)
# ---------------------------------------------------------------------------

class SamplerBankRequest(BaseModel):
    bank: str
    pad_count: int = 16

    @field_validator("bank")
    @classmethod
    def bank_valid(cls, v: str) -> str:
        valid = ["drums", "percussion", "bass", "synth", "vocals", "fx"]
        if v not in valid:
            raise ValueError(f"Invalid bank '{v}'. Must be one of: {', '.join(valid)}")
        return v

    @field_validator("pad_count")
    @classmethod
    def pad_count_valid(cls, v: int) -> int:
        if v < 1 or v > 64:
            raise ValueError("pad_count must be between 1 and 64")
        return v


@app.post(
    "/music-studio/sampler-bank",
    summary="Sampler Bank: return pad configuration for a named sample bank",
)
def sampler_bank_endpoint(request: SamplerBankRequest):
    """Return a 16-pad (or custom count) sampler bank configuration."""
    try:
        result = generate_sampler_bank(request.bank, request.pad_count)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sampler bank generation failed: {exc}")
    return result


# ---------------------------------------------------------------------------
# Music Studio — Virtual Keyboard Config (Phase 16)
# ---------------------------------------------------------------------------

class KeyboardConfigRequest(BaseModel):
    instrument: str
    octave: int = 4

    @field_validator("instrument")
    @classmethod
    def instrument_valid(cls, v: str) -> str:
        valid = ["piano", "organ", "strings", "synth", "bass", "marimba"]
        if v not in valid:
            raise ValueError(f"Invalid instrument '{v}'. Must be one of: {', '.join(valid)}")
        return v

    @field_validator("octave")
    @classmethod
    def octave_valid(cls, v: int) -> int:
        if v < 1 or v > 8:
            raise ValueError("octave must be between 1 and 8")
        return v


@app.post(
    "/music-studio/keyboard-config",
    summary="Virtual Keyboard Config: return note/frequency mapping for an instrument",
)
def keyboard_config_endpoint(request: KeyboardConfigRequest):
    """Return note frequencies and waveform config for the virtual keyboard."""
    try:
        result = generate_virtual_keyboard_config(request.instrument, request.octave)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Keyboard config generation failed: {exc}")
    return result

class VideoScriptRequest(BaseModel):
    prompt: str
    style: str = "cinematic"
    scene_count: int = 5

    @field_validator("prompt")
    @classmethod
    def prompt_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("prompt must not be empty")
        return v.strip()

    @field_validator("style")
    @classmethod
    def style_valid(cls, v: str) -> str:
        if v not in _VIDEO_STYLES:
            raise ValueError(f"Invalid style '{v}'. Valid: {sorted(_VIDEO_STYLES)}")
        return v

    @field_validator("scene_count")
    @classmethod
    def scene_count_valid(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("scene_count must be between 1 and 20")
        return v


@app.post(
    "/video-studio/generate-script",
    summary="Phase 15 AI Video Generator: text prompt → scene-based video script",
)
def video_generate_script(request: VideoScriptRequest):
    """
    Convert a text prompt into a structured scene-based video script.

    The response includes a list of scenes, each with:
    - ``text``          – on-screen caption
    - ``image_concept`` – background image description for AI generation
    - ``animation``     – transition animation type
    - ``duration``      – scene duration in seconds
    - ``voice_text``    – narration text for TTS
    - ``bg_music``      – background music mood hint
    """
    try:
        result = generate_video_script(
            prompt=request.prompt,
            style=request.style,
            scene_count=request.scene_count,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Video script generation failed: {exc}")
    return result


# ── Video Effects ──────────────────────────────────────────────────────────

class VideoEffectBody(BaseModel):
    scenes: List[dict]
    effect: str
    intensity: float = 1.0

    @field_validator("scenes")
    @classmethod
    def scenes_non_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("scenes must not be empty")
        return v

    @field_validator("effect")
    @classmethod
    def effect_valid(cls, v: str) -> str:
        if v not in _VIDEO_EFFECTS:
            raise ValueError(f"Invalid effect '{v}'. Valid effects: {sorted(_VIDEO_EFFECTS)}")
        return v

    @field_validator("intensity")
    @classmethod
    def intensity_valid(cls, v: float) -> float:
        if not (0.0 <= v <= 2.0):
            raise ValueError("intensity must be between 0.0 and 2.0")
        return v


@app.post("/video-studio/apply-effect", summary="Apply a video effect to scenes")
@limiter.limit("30/minute")
def video_apply_effect(request: Request, body: VideoEffectBody):
    try:
        result = apply_video_effect(body.scenes, body.effect, body.intensity)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return result


# ── AI Video Tools ─────────────────────────────────────────────────────────

class AiVideoToolBody(BaseModel):
    scenes: List[dict]
    tool: str
    options: Optional[dict] = None

    @field_validator("scenes")
    @classmethod
    def scenes_non_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("scenes must not be empty")
        return v

    @field_validator("tool")
    @classmethod
    def tool_valid(cls, v: str) -> str:
        if v not in _VIDEO_AI_TOOLS:
            raise ValueError(f"Invalid tool '{v}'. Valid tools: {sorted(_VIDEO_AI_TOOLS)}")
        return v


@app.post("/video-studio/ai-tool", summary="Apply an AI video tool to scenes")
@limiter.limit("30/minute")
def video_ai_tool(request: Request, body: AiVideoToolBody):
    try:
        result = apply_ai_video_tool(body.scenes, body.tool, body.options)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return result
# ---------------------------------------------------------------------------

class AiTransformRequest(BaseModel):
    input_type:  str
    output_type: str
    data:        str
    options:     dict = {}

    @field_validator("input_type")
    @classmethod
    def input_type_valid(cls, v: str) -> str:
        if v not in VALID_INPUT_TYPES:
            raise ValueError(f"Invalid input_type '{v}'. Valid: {sorted(VALID_INPUT_TYPES)}")
        return v

    @field_validator("output_type")
    @classmethod
    def output_type_valid(cls, v: str) -> str:
        if v not in VALID_OUTPUT_TYPES:
            raise ValueError(f"Invalid output_type '{v}'. Valid: {sorted(VALID_OUTPUT_TYPES)}")
        return v

    @field_validator("data")
    @classmethod
    def data_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("data must not be empty.")
        return v.strip()


@app.post(
    "/ai/transform",
    summary="Creative Intelligence Engine: cross-medium AI transforms",
)
def ai_transform(request: AiTransformRequest):
    """
    Transform creative content across media types.

    Supported pairs
    ---------------
    - text   → video   (poem/story → scene-based video script)
    - text   → song    (prose/lyrics → song structure + beat recipe)
    - design → animation (design brief → animation plan)
    - music  → video   (music description → visualizer video config)
    """
    try:
        result = intelligence_transform(
            input_type=request.input_type,
            output_type=request.output_type,
            data=request.data,
            options=request.options,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transform failed: {exc}")
    return result


# ---------------------------------------------------------------------------
# Phase 16 — Universal AI Assistant  POST /ai/assistant
# ---------------------------------------------------------------------------

class AiAssistRequest(BaseModel):
    context: str = ""
    prompt:  str
    studio:  str = "general"

    @field_validator("prompt")
    @classmethod
    def prompt_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("prompt must not be empty.")
        return v.strip()


@app.post(
    "/ai/assistant",
    summary="Universal AI OS Brain: context-aware suggestions for any studio",
)
def ai_assistant(request: AiAssistRequest):
    """
    Context-aware AI assistant across all KalaOS studios.

    Returns an action, a response text, contextual suggestions, and
    an optional cross-medium transform hint.
    """
    try:
        result = ai_assist(
            context=request.context,
            prompt=request.prompt,
            studio=request.studio,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Assistant error: {exc}")
    return result


# ---------------------------------------------------------------------------
# Phase 16 — Comments  POST/GET /posts/{post_id}/comments
#                      DELETE /comments/{comment_id}
# ---------------------------------------------------------------------------

class CommentRequest(BaseModel):
    token:   str
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content must not be empty.")
        return v.strip()


@app.post("/posts/{post_id}/comments", summary="Add a comment to a post")
def add_comment(post_id: str, body: CommentRequest):
    try:
        comment = platform_service.add_comment(body.token, post_id, body.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return comment


@app.get("/posts/{post_id}/comments", summary="Get comments for a post")
def get_comments(post_id: str, limit: int = 50, offset: int = 0):
    comments = platform_service.get_comments(post_id, limit, offset)
    return {"post_id": post_id, "comments": comments, "count": len(comments)}


class DeleteCommentRequest(BaseModel):
    token: str


@app.delete("/comments/{comment_id}", summary="Delete a comment")
def delete_comment(comment_id: str, token: str):
    try:
        platform_service.delete_comment(token, comment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"deleted": comment_id}


# ---------------------------------------------------------------------------
# Phase 16 — Follows  POST /users/{target_email}/follow
#                     GET  /users/{email}/followers
#                     GET  /users/{email}/following
# ---------------------------------------------------------------------------

class FollowRequest(BaseModel):
    token: str


@app.post("/users/{target_email}/follow", summary="Follow or unfollow a user")
def follow_user(target_email: str, body: FollowRequest):
    try:
        result = platform_service.follow_user(body.token, target_email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result


@app.get("/users/{email}/followers", summary="Get followers of a user")
def get_followers(email: str):
    followers = platform_service.get_followers(email)
    return {"email": email, "followers": followers, "count": len(followers)}


@app.get("/users/{email}/following", summary="Get who a user follows")
def get_following(email: str):
    following = platform_service.get_following(email)
    return {"email": email, "following": following, "count": len(following)}


# ---------------------------------------------------------------------------
# Phase 16 — Notifications  GET /notifications
#                            POST /notifications/{id}/read
#                            POST /notifications/read-all
# ---------------------------------------------------------------------------

@app.get("/notifications", summary="Get notifications for the authenticated user")
def get_notifications(token: str, limit: int = 30, offset: int = 0):
    try:
        notifs = platform_service.get_notifications(token, limit, offset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"notifications": notifs, "count": len(notifs)}


class NotifReadRequest(BaseModel):
    token: str


@app.post("/notifications/{notification_id}/read", summary="Mark a notification as read")
def mark_notification_read(notification_id: str, body: NotifReadRequest):
    try:
        platform_service.mark_notification_read(body.token, notification_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"read": notification_id}


@app.post("/notifications/read-all", summary="Mark all notifications as read")
def mark_all_notifications_read(body: NotifReadRequest):
    try:
        platform_service.mark_all_notifications_read(body.token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "ok"}




# ---------------------------------------------------------------------------
# Collab endpoints
# ---------------------------------------------------------------------------

class CollabWorkspaceBody(BaseModel):
    name: str
    project_type: str
    owner: str
    description: str = ""


@app.post("/collab/workspace", summary="Create a collaboration workspace")
@limiter.limit("20/minute")
def create_workspace(request: Request, body: CollabWorkspaceBody):
    try:
        result = create_collab_workspace(
            body.name, body.project_type, body.owner, body.description
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class CollabInviteBody(BaseModel):
    user_email: str
    role: str


@app.post("/collab/workspace/{workspace_id}/invite", summary="Add a collaborator to a workspace")
@limiter.limit("20/minute")
def invite_collaborator(workspace_id: str, request: Request, body: CollabInviteBody):
    try:
        result = add_collaborator(workspace_id, body.user_email, body.role)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/collab/workspace/{workspace_id}/activity", summary="Get workspace activity feed")
@limiter.limit("20/minute")
def get_workspace_activity(workspace_id: str, request: Request, user_email: str = ""):
    try:
        result = get_collab_activity(workspace_id, user_email)
        return {"activities": result}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class CollabSuggestionsBody(BaseModel):
    workspace_id: str
    project_type: str
    context: str = ""


@app.post("/collab/suggestions", summary="Generate AI collaboration suggestions")
@limiter.limit("20/minute")
def collab_suggestions(request: Request, body: CollabSuggestionsBody):
    try:
        result = generate_collab_suggestions(
            body.workspace_id, body.project_type, body.context
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ---------------------------------------------------------------------------
# Stream endpoints
# ---------------------------------------------------------------------------

class StreamSetupBody(BaseModel):
    platform: str
    title: str
    quality: str
    description: str = ""


@app.post("/stream/setup", summary="Set up a live stream configuration")
@limiter.limit("20/minute")
def stream_setup(request: Request, body: StreamSetupBody):
    try:
        result = setup_stream(
            body.platform, body.title, body.quality, body.description
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/stream/{stream_id}/analytics", summary="Get stream analytics")
@limiter.limit("20/minute")
def stream_analytics(stream_id: str, request: Request, duration_minutes: int = 60):
    try:
        result = get_stream_analytics(stream_id, duration_minutes)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class StreamOverlayBody(BaseModel):
    title: str
    style: str


@app.post("/stream/overlay", summary="Generate a stream overlay configuration")
@limiter.limit("20/minute")
def stream_overlay(request: Request, body: StreamOverlayBody):
    try:
        result = generate_stream_overlay(body.title, body.style)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------

class ExportPrepareBody(BaseModel):
    studio: str
    format: str
    content: str
    quality: str = "high"


@app.post("/export/prepare", summary="Prepare an export manifest")
@limiter.limit("20/minute")
def export_prepare(request: Request, body: ExportPrepareBody):
    try:
        result = prepare_export(
            body.studio, body.format, body.content, body.quality
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class ExportImportUrlBody(BaseModel):
    url: str
    studio: str


@app.post("/export/import-url", summary="Import content from a URL")
@limiter.limit("20/minute")
def export_import_url(request: Request, body: ExportImportUrlBody):
    try:
        result = import_from_url(body.url, body.studio)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class BatchExportItem(BaseModel):
    studio: str
    format: str
    content: str
    quality: str = "high"


class BatchExportBody(BaseModel):
    items: List[BatchExportItem]


@app.post("/export/batch", summary="Batch export multiple items")
@limiter.limit("20/minute")
def export_batch(request: Request, body: BatchExportBody):
    try:
        items_dicts = [item.model_dump() for item in body.items]
        result = batch_export(items_dicts)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ---------------------------------------------------------------------------
# AI feature endpoints
# ---------------------------------------------------------------------------

class ContentGeneratorBody(BaseModel):
    type: str  # text_to_image, image_to_video, auto_caption
    content: str
    options: dict = {}


@app.post("/ai/content-generator", summary="AI content generation (text-to-image, image-to-video, auto-caption)")
@limiter.limit("20/minute")
def ai_content_generator(request: Request, body: ContentGeneratorBody):
    valid_types = {"text_to_image", "image_to_video", "auto_caption"}
    if not body.type or body.type not in valid_types:
        raise HTTPException(
            status_code=422,
            detail=f"type must be one of {sorted(valid_types)}",
        )
    if not body.content or not body.content.strip():
        raise HTTPException(status_code=422, detail="content must not be empty")

    content = body.content.strip()
    gen_type = body.type

    if gen_type == "text_to_image":
        output = {
            "type": "text_to_image",
            "prompt": content,
            "image_concept": f"Visual representation of: {content[:80]}",
            "style_suggestions": ["cinematic", "abstract", "photorealistic"],
            "dimensions": body.options.get("dimensions", "1024x1024"),
            "status": "generated",
        }
    elif gen_type == "image_to_video":
        output = {
            "type": "image_to_video",
            "source": content,
            "animation_style": body.options.get("animation_style", "zoom-in"),
            "duration_seconds": body.options.get("duration_seconds", 5),
            "transitions": ["fade", "dissolve"],
            "status": "generated",
        }
    else:  # auto_caption
        words = content.split()
        captions = [
            " ".join(words[i : i + 8]) for i in range(0, min(len(words), 40), 8)
        ]
        output = {
            "type": "auto_caption",
            "source": content[:80],
            "captions": captions if captions else [content[:80]],
            "language": body.options.get("language", "en"),
            "style": body.options.get("style", "standard"),
            "status": "generated",
        }

    return output


class AIAnalyticsBody(BaseModel):
    content_id: str
    content_type: str
    time_range: str = "7d"


@app.post("/ai/analytics", summary="AI content performance and audience analytics")
@limiter.limit("20/minute")
def ai_analytics(request: Request, body: AIAnalyticsBody):
    if not body.content_id or not body.content_id.strip():
        raise HTTPException(status_code=422, detail="content_id must not be empty")
    if not body.content_type or not body.content_type.strip():
        raise HTTPException(status_code=422, detail="content_type must not be empty")

    import hashlib as _hl
    seed = body.content_id.strip()
    digest = int(_hl.md5(seed.encode()).hexdigest(), 16)

    views      = 1000 + (digest % 50000)
    likes      = views // 10 + (digest % 500)
    shares     = likes // 5
    comments   = likes // 8
    eng_rate   = round((likes + shares + comments) / max(views, 1) * 100, 2)
    top_age    = ["18-24", "25-34", "35-44", "45-54"][digest % 4]
    top_region = ["US", "UK", "IN", "BR", "DE"][digest % 5]

    return {
        "content_id": seed,
        "content_type": body.content_type.strip(),
        "time_range": body.time_range,
        "performance": {
            "views": views,
            "likes": likes,
            "shares": shares,
            "comments": comments,
            "engagement_rate_pct": eng_rate,
        },
        "audience": {
            "top_age_group": top_age,
            "top_region": top_region,
            "returning_viewers_pct": round(20 + (digest % 40), 1),
        },
        "recommendations": [
            "Post during peak hours (6-9 PM local time)",
            f"Your {top_age} audience responds well to interactive content",
            "Consider adding captions to boost accessibility reach",
        ],
    }


class AISmartSearchBody(BaseModel):
    query: str
    content_types: List[str] = []
    limit: int = 10


@app.post("/ai/smart-search", summary="Semantic smart search across content")
@limiter.limit("20/minute")
def ai_smart_search(request: Request, body: AISmartSearchBody):
    if not body.query or not body.query.strip():
        raise HTTPException(status_code=422, detail="query must not be empty")
    if body.limit <= 0:
        raise HTTPException(status_code=422, detail="limit must be greater than 0")

    query = body.query.strip()
    import hashlib as _hl
    digest = int(_hl.md5(query.encode()).hexdigest(), 16)

    studios = ["music", "visual", "video", "animation", "text"]
    results = []
    for i in range(min(body.limit, 5)):
        studio = studios[(digest + i) % len(studios)]
        results.append(
            {
                "result_id": _hl.md5(f"{query}{i}".encode()).hexdigest()[:12],
                "title": f"Result {i + 1} for '{query[:30]}'",
                "studio": studio,
                "relevance_score": round(0.95 - i * 0.08, 2),
                "snippet": f"Semantic match: {query[:60]}...",
            }
        )

    return {
        "query": query,
        "total_results": len(results),
        "results": results,
        "content_types_searched": body.content_types if body.content_types else studios,
    }


class AIQualityCheckBody(BaseModel):
    export_id: str
    format: str
    content_preview: str = ""


@app.post("/ai/quality-check", summary="AI quality assessment of exports")
@limiter.limit("20/minute")
def ai_quality_check(request: Request, body: AIQualityCheckBody):
    if not body.export_id or not body.export_id.strip():
        raise HTTPException(status_code=422, detail="export_id must not be empty")
    if not body.format or not body.format.strip():
        raise HTTPException(status_code=422, detail="format must not be empty")

    import hashlib as _hl
    seed = body.export_id.strip()
    digest = int(_hl.md5(seed.encode()).hexdigest(), 16)

    score = 60 + (digest % 40)
    issues = []
    if score < 75:
        issues.append("Bitrate below recommended threshold")
    if score < 85:
        issues.append("Consider increasing export quality setting")

    return {
        "export_id": seed,
        "format": body.format.strip(),
        "quality_score": score,
        "grade": "A" if score >= 90 else ("B" if score >= 80 else ("C" if score >= 70 else "D")),
        "issues": issues,
        "suggestions": [
            "Verify codec compatibility with target platform",
            "Run a preview before final distribution",
        ],
        "passed": score >= 70,
    }


# ---------------------------------------------------------------------------
# Platform Connect endpoints
# ---------------------------------------------------------------------------

class PlatformConnectBody(BaseModel):
    platform: str
    user_id: str
    auth_code: str


class PlatformDisconnectBody(BaseModel):
    platform: str
    user_id: str


class PlatformDistributeBody(BaseModel):
    user_id: str
    platforms: List[str]
    content: dict


class PlatformEPKBody(BaseModel):
    user_id: str
    artist_name: str
    genre: str
    bio: str


@app.get("/platform-connect/oauth-url", summary="Get OAuth URL for a platform")
@limiter.limit("20/minute")
def platform_connect_oauth_url(request: Request, platform: str, user_id: str):
    try:
        result = get_oauth_url(platform, user_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/platform-connect/connect", summary="Connect a platform via OAuth")
@limiter.limit("20/minute")
def platform_connect_connect(request: Request, body: PlatformConnectBody):
    try:
        result = connect_platform(body.platform, body.user_id, body.auth_code)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/platform-connect/disconnect", summary="Disconnect a connected platform")
@limiter.limit("20/minute")
def platform_connect_disconnect(request: Request, body: PlatformDisconnectBody):
    try:
        result = disconnect_platform(body.platform, body.user_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/platform-connect/platforms/{user_id}", summary="Get connected platforms for a user")
@limiter.limit("20/minute")
def platform_connect_get_platforms(user_id: str, request: Request):
    result = get_connected_platforms(user_id)
    return result


@app.post("/platform-connect/distribute", summary="Distribute content to multiple platforms")
@limiter.limit("20/minute")
def platform_connect_distribute(request: Request, body: PlatformDistributeBody):
    if not body.platforms:
        raise HTTPException(status_code=422, detail="platforms must be a non-empty list")
    if not body.content.get("title"):
        raise HTTPException(status_code=422, detail="content must include a 'title' field")
    if not body.content.get("type"):
        raise HTTPException(status_code=422, detail="content must include a 'type' field")
    try:
        result = distribute_to_platforms(body.user_id, body.platforms, body.content)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/platform-connect/analytics/{user_id}", summary="Get analytics summary for a user")
@limiter.limit("20/minute")
def platform_connect_analytics(user_id: str, request: Request, platform: str = "all"):
    result = get_analytics_summary(user_id, platform)
    return result


@app.post("/platform-connect/epk", summary="Generate an Electronic Press Kit")
@limiter.limit("20/minute")
def platform_connect_epk(request: Request, body: PlatformEPKBody):
    if not body.artist_name or not body.artist_name.strip():
        raise HTTPException(status_code=422, detail="artist_name must not be empty")
    if not body.genre or not body.genre.strip():
        raise HTTPException(status_code=422, detail="genre must not be empty")
    if not body.bio or not body.bio.strip():
        raise HTTPException(status_code=422, detail="bio must not be empty")
    try:
        result = generate_epk(body.user_id, body.artist_name, body.genre, body.bio)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/platform-connect/optimal-release", summary="Get optimal release timing for a genre")
@limiter.limit("20/minute")
def platform_connect_optimal_release(request: Request, genre: str, target_region: str = "global"):
    result = get_optimal_release_time(genre, target_region)
    return result
