"""LLM explainer — explains a ranking in plain English / Odia / Hindi.

Uses only already-computed facts. Falls back to a deterministic template
when there is no key, no network, a timeout, or a failed post-check.
"""
import hashlib
import json
import os
import time
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "none").lower()
LLM_TIMEOUT = 8  # seconds
_cache: dict[str, str] = {}

SYSTEM_PROMPT = """You are a hospital recommendation assistant for Bhubaneswar, Odisha.
Rules:
- Use ONLY the facts provided in the JSON. Never invent facts.
- Say "unknown" when a fact is missing.
- No medical advice.
- Mention which ranking method was used and that data is a demo snapshot.
- Maximum 120 words.
- Language: {language} (en=English, or=Odia, hi=Hindi).
- Label your response as "machine-generated"."""


def _hash_facts(facts: dict) -> str:
    return hashlib.md5(json.dumps(facts, sort_keys=True).encode()).hexdigest()


def _template_fallback(facts: dict, language: str = "en") -> str:
    """Deterministic f-string fallback — always works, no network needed."""
    method = facts.get("method", "Mentor formula")
    top = facts.get("top_hospitals", [])
    location = facts.get("location_name", "your location")

    if not top:
        return f"No hospitals to explain. [machine-generated, {method}]"

    h1 = top[0] if len(top) > 0 else {}
    lines = [f"📊 **Ranking Explanation** ({method})", ""]

    if method == "Mentor formula":
        lines.append(
            f"Using the mentor's formula: `Score = (Rating × Reviews) × 100 − Distance − Fee`, "
            f"**{h1.get('name', '?')}** ranks #1 from {location} with a score of "
            f"{h1.get('score', '?'):,.0f} "
            f"(rating {h1.get('rating', '?')}, {h1.get('reviews', '?'):,} reviews, "
            f"Rs {h1.get('fee', '?')}/day, {h1.get('distance', '?')} km away)."
        )
        lines.append("")
        lines.append(
            "⚠️ Note: This formula is dominated by rating × reviews. Distance and fee "
            "have minimal impact on the ranking. Try the **Balanced** method for "
            "location-aware recommendations."
        )
    else:
        lines.append(
            f"Using the **Balanced** method from {location}: "
            f"**{h1.get('name', '?')}** ranks #1 "
            f"({h1.get('distance', '?')} km, Rs {h1.get('fee', '?')}/day, "
            f"rating {h1.get('rating', '?')}, "
            f"bed availability: {h1.get('availability', '?')})."
        )
        lines.append("")
        lines.append(
            "This score balances rating (25%), distance (30%), fee (20%), and "
            "predicted bed availability (25%)."
        )

    if len(top) > 1:
        h2 = top[1]
        lines.append(
            f"Runner-up: **{h2.get('name', '?')}** "
            f"({h2.get('distance', '?')} km, Rs {h2.get('fee', '?')}/day)."
        )

    lines.append("")
    lines.append("*Demo snapshot — occupancy data is simulated. [machine-generated]*")
    return "\n".join(lines)


def _post_check(response: str, facts: dict) -> bool:
    """Verify every number in the LLM response appears in the input facts."""
    import re
    facts_str = json.dumps(facts)
    numbers_in_response = set(re.findall(r'\d+\.?\d*', response))
    numbers_in_facts = set(re.findall(r'\d+\.?\d*', facts_str))
    # Allow common numbers like 1, 2, 3 and percentages
    suspicious = numbers_in_response - numbers_in_facts - {'0', '1', '2', '3', '100', '25', '30', '20'}
    return len(suspicious) == 0


def _call_gemini(facts: dict, language: str) -> str | None:
    """Call Gemini API. Returns None on failure."""
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = SYSTEM_PROMPT.format(language=language) + f"\n\nFacts:\n```json\n{json.dumps(facts, indent=2)}\n```"
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return None


def _call_openai(facts: dict, language: str) -> str | None:
    """Call OpenAI API. Returns None on failure."""
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return None
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(language=language)},
                {"role": "user", "content": f"Facts:\n{json.dumps(facts, indent=2)}"},
            ],
            max_tokens=300,
            timeout=LLM_TIMEOUT,
        )
        return response.choices[0].message.content
    except Exception:
        return None


def _call_groq(facts: dict, language: str) -> str | None:
    """Call Groq API (free, fast). Uses OpenAI-compatible format."""
    try:
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            return None
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(language=language)},
                {"role": "user", "content": f"Facts:\n{json.dumps(facts, indent=2)}"},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception:
        return None


def explain(facts: dict, language: str = "en") -> str:
    """Generate a plain-language explanation of the ranking.

    Parameters
    ----------
    facts : dict with keys like method, location_name, top_hospitals (list of dicts)
    language : "en", "or", or "hi"

    Returns
    -------
    str : explanation text (always returns something, never blocks)
    """
    key = _hash_facts(facts) + language
    if key in _cache:
        return _cache[key]

    result = None

    if LLM_PROVIDER == "groq":
        result = _call_groq(facts, language)
    elif LLM_PROVIDER == "gemini":
        result = _call_gemini(facts, language)
    elif LLM_PROVIDER == "openai":
        result = _call_openai(facts, language)

    # Post-check: verify no fabricated numbers
    if result and not _post_check(result, facts):
        result = None  # discard, use template

    if result is None:
        result = _template_fallback(facts, language)

    _cache[key] = result
    return result
