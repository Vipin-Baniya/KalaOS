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

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from typing import Literal, Optional

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
from services.llm_service import generate_explanation, generate_suggestions, ART_DOMAINS

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
