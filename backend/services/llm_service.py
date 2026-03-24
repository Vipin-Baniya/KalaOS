"""
LLM Service – Ollama Integration
---------------------------------
Connects to a locally running Ollama instance (http://localhost:11434)
and generates a respectful, insightful explanation of artistic patterns
detected by KalaCore.

Requires Ollama to be running locally with a model pulled
(default: "llama3").
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict

logger = logging.getLogger(__name__)


OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3"

# Timeout constants (seconds) — explanation is faster; suggestions need more time
_EXPLANATION_TIMEOUT = 30
_SUGGESTIONS_TIMEOUT = 60

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
