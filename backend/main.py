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
"""

import logging
import os as _os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from typing import Literal, Optional

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
from services.llm_service import (
    generate_explanation,
    generate_suggestions,
    generate_deep_narrative,
    list_available_models,
    ART_DOMAINS,
)
import services.auth_service as auth_service

# Build the domain Literal dynamically from ART_DOMAINS so there is
# only one source of truth for the allowed values.
ArtDomain = Literal["lyrics", "poetry", "music", "story", "book", "general"]  # type: ignore[assignment]
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
_login_limit  = _os.environ.get("KALA_RATE_LIMIT_LOGIN",  "10/minute")
_forgot_limit = _os.environ.get("KALA_RATE_LIMIT_FORGOT", "5/minute")
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
# Auth – Registration, Login, Forgot/Reset Password
# ---------------------------------------------------------------------------

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


class AuthChangePasswordRequest(BaseModel):
    token: str
    old_password: str
    new_password: str


@app.post("/auth/register", summary="Register a new artist account")
def auth_register(request: AuthRegisterRequest):
    """Create a new user account.  Returns public user info on success."""
    try:
        user = auth_service.register(request.email, request.password, request.name)
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


@app.post("/auth/update-profile", summary="Update display name")
def auth_update_profile(request: AuthUpdateProfileRequest):
    """Update the display name for the authenticated user."""
    try:
        user = auth_service.update_profile(request.token, request.name)
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
