"""
LLM Service – Ollama Integration
---------------------------------
Connects to a locally running Ollama instance (http://localhost:11434)
and generates respectful, insightful explanations of artistic patterns
detected by KalaCore.

Requires Ollama to be running locally with a model pulled.
Default model: "llama3" — override via the ``model`` parameter on any
public function, or set ``DEFAULT_MODEL`` for global override.

Public API
----------
generate_explanation(analysis, model)           – pattern explanation (Phase 1)
generate_suggestions(text, analysis, domain, model) – improvement suggestions
generate_deep_narrative(all_data, model)        – Phase 8 unified narrative
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict

logger = logging.getLogger(__name__)


OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3"

# Timeout constants (seconds) — explanation is faster; suggestions / deep narrative need more time
_EXPLANATION_TIMEOUT = 30
_SUGGESTIONS_TIMEOUT = 60
_DEEP_NARRATIVE_TIMEOUT = 90

# Supported art domains and their human-readable labels used in prompts
ART_DOMAINS = {
    "lyrics": "song lyrics",
    "poetry": "poetry",
    "music": "music composition or production notes",
    "story": "short story or narrative",
    "book": "book or long-form writing",
    "general": "creative writing",
}


def _build_prompt(analysis: Dict[str, Any]) -> str:
    """
    Construct a prompt that asks the LLM to explain the artistic patterns
    in a respectful, non-judgmental tone.
    """
    # Summarise key figures for the prompt
    rhyme_density = analysis.get("art_genome", {}).get("rhyme_density", 0)
    symmetry = analysis.get("art_genome", {}).get("symmetry_score", 0)
    complexity = analysis.get("art_genome", {}).get("complexity_score", 0)
    pal_count = (
        analysis.get("analysis", {})
        .get("palindrome", {})
        .get("full_palindrome_count", 0)
    )
    refrains = (
        analysis.get("analysis", {})
        .get("structure", {})
        .get("refrains", [])
    )

    prompt = (
        "You are an art analyst who respects every form of artistic expression. "
        "Your role is to illuminate patterns — never to judge quality.\n\n"
        "Here are the structural metrics of a piece of art (lyrics or poem):\n"
        f"  - Rhyme density: {rhyme_density:.2f} (0 = no rhymes, 1 = all lines rhyme)\n"
        f"  - Symmetry score: {symmetry:.1f} (1 = mirror structure)\n"
        f"  - Complexity score: {complexity:.2f} (heuristic, 0–1)\n"
        f"  - Full palindrome lines: {pal_count}\n"
        f"  - Refrains detected: {', '.join(refrains) if refrains else 'none'}\n\n"
        "Please write 2–3 sentences explaining what these patterns suggest about "
        "the artistic choices in this piece. Be warm, curious, and supportive."
    )
    return prompt


def generate_explanation(analysis: Dict[str, Any], model: str = DEFAULT_MODEL) -> str:
    """
    Send the analysis to Ollama and return a natural-language explanation.

    Parameters
    ----------
    analysis : dict
        The combined output from the /analyze-art endpoint
        (must contain 'art_genome' and 'analysis' keys).
    model : str
        Name of the Ollama model to use (default: "llama3").

    Returns
    -------
    str
        The LLM-generated explanation, or an error message if Ollama is
        unavailable.
    """
    prompt = _build_prompt(analysis)
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")

    request = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=_EXPLANATION_TIMEOUT) as response:
            body = json.loads(response.read().decode("utf-8"))
            return body.get("response", "").strip()
    except urllib.error.URLError as exc:
        # Ollama may not be running locally — return a graceful fallback
        return (
            f"[LLM unavailable: {exc.reason}] "
            "Artistic analysis completed — install and run Ollama locally "
            "to receive natural-language explanations."
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error while calling Ollama: %s", exc)
        return "[LLM error: an unexpected error occurred. Check server logs for details.]"


# ---------------------------------------------------------------------------
# Suggestions / Improvements
# ---------------------------------------------------------------------------

def _build_suggestions_prompt(
    text: str, analysis: Dict[str, Any], domain: str
) -> str:
    """
    Build a prompt that asks the LLM to provide respectful, actionable
    improvement suggestions for the artist's work.
    """
    domain_label = ART_DOMAINS.get(domain, ART_DOMAINS["general"])
    rhyme_density = analysis.get("art_genome", {}).get("rhyme_density", 0)
    complexity = analysis.get("art_genome", {}).get("complexity_score", 0)
    refrains = (
        analysis.get("analysis", {})
        .get("structure", {})
        .get("refrains", [])
    )
    internal_rhyme_lines = [
        r["line"]
        for r in analysis.get("analysis", {})
        .get("rhymes", {})
        .get("internal_rhymes", [])
        if r.get("has_internal_rhyme")
    ]

    prompt = (
        f"You are a warm and encouraging artistic mentor specialising in {domain_label}. "
        "Your suggestions always honour the artist's voice and original intent. "
        "You never rewrite their work — you only offer gentle, specific ideas they may choose to explore.\n\n"
        f"The artist has shared the following {domain_label}:\n"
        "---\n"
        f"{text.strip()}\n"
        "---\n\n"
        "Structural observations:\n"
        f"  - Rhyme density: {rhyme_density:.2f} (0 = no end-rhymes, 1 = all lines rhyme)\n"
        f"  - Complexity score: {complexity:.2f} (0–1 heuristic)\n"
        f"  - Refrains detected: {', '.join(refrains) if refrains else 'none'}\n"
        f"  - Lines with internal rhyme: {len(internal_rhyme_lines)}\n\n"
        "Please provide 3–5 specific, encouraging suggestions to help the artist "
        f"strengthen this piece of {domain_label}. "
        "Focus on structure, imagery, rhythm, or emotional impact as appropriate. "
        "Number each suggestion. Keep the tone warm, respectful, and supportive — "
        "this is collaboration, not critique."
    )
    return prompt


def generate_suggestions(
    text: str,
    analysis: Dict[str, Any],
    domain: str = "general",
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Generate artist-friendly improvement suggestions via Ollama.

    Parameters
    ----------
    text : str
        The original text submitted by the artist.
    analysis : dict
        The combined pipeline output (must contain 'art_genome' and 'analysis').
    domain : str
        Art domain — one of: lyrics, poetry, music, story, book, general.
    model : str
        Ollama model name (default: "llama3").

    Returns
    -------
    str
        Numbered suggestions from the LLM, or a graceful fallback message.
    """
    # Normalise domain; fall back to "general" for unknown values
    if domain not in ART_DOMAINS:
        domain = "general"

    prompt = _build_suggestions_prompt(text, analysis, domain)
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")

    request = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=_SUGGESTIONS_TIMEOUT) as response:
            body = json.loads(response.read().decode("utf-8"))
            return body.get("response", "").strip()
    except urllib.error.URLError as exc:
        return (
            f"[LLM unavailable: {exc.reason}] "
            "Your art has been analysed — run Ollama locally to receive "
            "personalised improvement suggestions."
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error generating suggestions: %s", exc)
        return "[LLM error: an unexpected error occurred. Check server logs for details.]"


# ---------------------------------------------------------------------------
# Shared low-level helper
# ---------------------------------------------------------------------------

def _call_ollama(prompt: str, model: str, timeout: int) -> str:
    """
    Send a prompt to the locally running Ollama instance and return the
    model's response text.  Returns a graceful fallback string on any error.
    """
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            return body.get("response", "").strip()
    except urllib.error.URLError as exc:
        return (
            f"[LLM unavailable: {exc.reason}] "
            "All structural analysis is complete — run Ollama locally "
            "to receive the full narrative."
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error calling Ollama: %s", exc)
        return "[LLM error: an unexpected error occurred. Check server logs for details.]"


# ---------------------------------------------------------------------------
# Phase 8 – Kala-LLM: Deep Narrative
# ---------------------------------------------------------------------------

def _build_deep_narrative_prompt(all_data: Dict[str, Any]) -> str:
    """
    Construct a rich, multi-phase prompt that asks the LLM to weave all of
    KalaOS's analysis layers into a single artist-facing narrative.

    The narrative honours the artist's intent across all dimensions:
    structure, craft, emotional truth, resonance, composition, distribution
    readiness, authorship, and temporal meaning.
    """
    # --- Extract key signals from each phase ---
    genome = all_data.get("art_genome", {})
    existential = all_data.get("existential", {})
    craft = all_data.get("craft", {})
    signal = all_data.get("signal", {})
    composition = all_data.get("composition", {})
    flow = all_data.get("flow", {})
    custody = all_data.get("custody", {})
    temporal = all_data.get("temporal", {})

    # Genome signals
    form = genome.get("form_type", "unknown")
    arc = genome.get("emotional_arc", {}).get("arc_direction", "unknown")
    mean_val = genome.get("emotional_arc", {}).get("mean_valence", 0.0)
    complexity = genome.get("complexity_score", 0.0)
    risk = genome.get("creative_risk_index", 0.0)
    rhyme_d = genome.get("rhyme_density", 0.0)

    # Existential signals
    creation_reason = existential.get("creation_reason", {}).get("primary_reason", "expression")
    survival = existential.get("survival", {}).get("is_survival_driven", False)
    necessity = existential.get("emotional_necessity", {}).get("necessity_score", 0.0)

    # Craft signals
    meter = craft.get("meter_flow", {}).get("dominant_meter", "free")
    breath_count = len(craft.get("breath_points", {}).get("breath_positions", []))

    # Signal (resonance)
    memorability = signal.get("memorability", {}).get("memorability_score", 0.0)
    longevity = signal.get("longevity", {}).get("longevity_score", 0.0)

    # Composition
    musical_feel = (
        composition.get("tempo", {}).get("feel", "unknown")
        if composition else "unknown"
    )
    scale_quality = (
        composition.get("chord_suggestions", {}).get("scale_quality", "unknown")
        if composition else "unknown"
    )

    # Flow (distribution)
    is_ready = flow.get("readiness", {}).get("is_ready", False) if flow else False
    primary_format = (
        flow.get("format_suitability", {}).get("primary_format", "unknown")
        if flow else "unknown"
    )

    # Custody / lineage
    primary_tradition = (
        custody.get("lineage", {}).get("primary_tradition", "unknown")
        if custody else "unknown"
    )

    # Temporal
    temporal_anchoring = (
        temporal.get("temporal_meaning", {}).get("temporal_anchoring", "unknown")
        if temporal else "unknown"
    )
    is_ephemeral = (
        temporal.get("ephemeral_classification", {}).get("is_ephemeral", False)
        if temporal else False
    )
    primary_ancestor = (
        temporal.get("creative_ancestry", {}).get("primary_ancestor", "unknown")
        if temporal else "unknown"
    )

    # Build the prompt
    prompt = (
        "You are KalaOS — an art intelligence that sees every piece of art as worthy "
        "of deep understanding. You speak directly to the artist with warmth, honesty, "
        "and deep respect. You never judge quality. You illuminate meaning.\n\n"
        "Here is a complete multi-dimensional analysis of the artist's work:\n\n"

        "--- STRUCTURE & FORM ---\n"
        f"  Form type: {form}\n"
        f"  Emotional arc: {arc} (mean valence: {mean_val:+.2f})\n"
        f"  Complexity score: {complexity:.2f}\n"
        f"  Creative risk index: {risk:.2f}\n"
        f"  Rhyme density: {rhyme_d:.2f}\n\n"

        "--- WHY IT WAS MADE ---\n"
        f"  Primary creation reason: {creation_reason}\n"
        f"  Survival-driven: {'yes' if survival else 'no'}\n"
        f"  Emotional necessity score: {necessity:.2f}\n\n"

        "--- CRAFT ---\n"
        f"  Dominant meter: {meter}\n"
        f"  Natural breath points: {breath_count}\n\n"

        "--- RESONANCE ---\n"
        f"  Memorability score: {memorability:.2f}\n"
        f"  Longevity score: {longevity:.2f}\n\n"

        "--- MUSICAL COMPOSITION ---\n"
        f"  Suggested feel: {musical_feel}\n"
        f"  Harmonic quality: {scale_quality}\n\n"

        "--- DISTRIBUTION & RELEASE ---\n"
        f"  Structurally complete / ready: {'yes' if is_ready else 'developing'}\n"
        f"  Natural format: {primary_format}\n\n"

        "--- AUTHORSHIP & LINEAGE ---\n"
        f"  Primary artistic tradition: {primary_tradition}\n\n"

        "--- TIME & MEANING ---\n"
        f"  Temporal anchoring: {temporal_anchoring}\n"
        f"  Ephemeral art: {'yes' if is_ephemeral else 'no'}\n"
        f"  Creative ancestor: {primary_ancestor}\n\n"

        "---\n\n"
        "Please write a 4–6 paragraph artist-facing narrative that:\n"
        "1. Acknowledges what this piece IS — its form, feeling, and intent.\n"
        "2. Speaks to WHY it was made and what emotional truth it carries.\n"
        "3. Notes what is distinctive about its craft and creative risk.\n"
        "4. Reflects on how it might move through the world — how it resonates, "
        "what format it naturally belongs to.\n"
        "5. Connects it to the tradition it inherits from, and how it will exist "
        "across time.\n\n"
        "Speak directly to the artist as 'you'. Be warm, specific, and truthful. "
        "This is a mirror, not a grade."
    )
    return prompt


def generate_deep_narrative(
    all_data: Dict[str, Any],
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Generate a unified artist-facing narrative from all KalaOS analysis layers.

    This is Phase 8's primary LLM function — it weaves structure, craft,
    emotional truth, resonance, composition, distribution, authorship, and
    temporal meaning into a single cohesive narrative.

    Parameters
    ----------
    all_data : dict
        Combined analysis data with keys: art_genome, existential, craft,
        signal, composition, flow, custody, temporal.
    model : str
        Ollama model name. Defaults to DEFAULT_MODEL ("llama3").

    Returns
    -------
    str
        The LLM-generated narrative, or a graceful fallback if Ollama is
        unavailable.
    """
    prompt = _build_deep_narrative_prompt(all_data)
    return _call_ollama(prompt, model, _DEEP_NARRATIVE_TIMEOUT)


def list_available_models() -> list:
    """
    Query the local Ollama instance for available models.

    Returns
    -------
    list of str
        Model names available locally, or empty list if Ollama is unavailable.
    """
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/tags",
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
            return [m["name"] for m in body.get("models", [])]
    except Exception:  # noqa: BLE001
        return []
