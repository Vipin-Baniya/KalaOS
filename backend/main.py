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
from kalacore.kalaproducer import produce, generate_ai_beat
from kalacore.kalaanimation import generate_animation_plan, parse_storyboard
from kalacore.kalavideo import generate_video_script, build_scene, _VALID_STYLES as _VIDEO_STYLES
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
# Video Studio — AI Video Generator (Phase 15)
# ---------------------------------------------------------------------------

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


