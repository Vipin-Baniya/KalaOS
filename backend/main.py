"""
KalaOS Backend – FastAPI Application
--------------------------------------
Entry point for the KalaOS API.

Endpoints
---------
GET  /            – health check
POST /analyze-art – full KalaCore + LLM pipeline
POST /suggest     – domain-aware artist improvement suggestions
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from typing import Literal

from kalacore.pattern_engine import analyze
from kalacore.art_genome import build_art_genome
from kalacore.ethics import check_request
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
