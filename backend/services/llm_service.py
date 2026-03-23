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
        with urllib.request.urlopen(request, timeout=30) as response:
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
