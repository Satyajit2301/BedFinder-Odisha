"""LLM explainer — explains a ranking in plain English / Odia / Hindi.

Calls Groq directly (no langchain-groq). Uses only already-computed facts.
Falls back to a deterministic template when there is no key, no network,
a timeout (8s), or a failed numeric post-check.
"""
import hashlib
import json
import os
import re
import time

from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq" if os.getenv("GROQ_API_KEY") else "none").lower()
LLM_TIMEOUT = 8  # seconds timeout
_cache: dict[str, str] = {}

SYSTEM_PROMPT = """You are a hospital recommendation assistant for Bhubaneswar, Odisha.
Rules:
- Use ONLY the facts provided in the JSON. Never invent facts or numbers.
- Say "unknown" when a fact is missing.
- No medical advice.
- Mention which ranking method was used and that bed occupancy is a demo snapshot.
- Maximum 120 words.
- Language: {language} (en=English, or=Odia, hi=Hindi).
- Label your response as "[machine-generated]"."""


def _hash_facts(facts: dict) -> str:
    return hashlib.md5(json.dumps(facts, sort_keys=True).encode()).hexdigest()


def _template_fallback(facts: dict, language: str = "en") -> str:
    """Deterministic f-string fallback — always works, no network needed."""
    method = facts.get("method", "Mentor formula (as given)")
    top = facts.get("top_hospitals", [])
    location = facts.get("location_name", "your location")

    if not top:
        return f"No hospitals to explain. [machine-generated, {method}]"

    h1 = top[0] if len(top) > 0 else {}
    lines = [f"📊 **Ranking Explanation** ({method})", ""]

    if "mentor" in method.lower():
        lines.append(
            f"Using the mentor's formula `Score = 100·A + X − Y − Z` "
            f"(where A is bed availability %, X is rating × reviews, Y is distance, Z is fee), "
            f"**{h1.get('name', '?')}** ranks #1 from {location} with a score of "
            f"{h1.get('score', 0):,.1f} "
            f"({h1.get('beds_free', '?')} beds free now, {h1.get('distance', '?')} km away, "
            f"Rs {h1.get('fee', '?')}/day, rating {h1.get('rating', '?')}★ with {h1.get('reviews', '?'):,} reviews)."
        )
        lines.append("")
        lines.append(
            "⚠️ Note: Review volume (X) reaches up to 149,545 and dominates the calculation. "
            "Switch to the **BedScore (recommended)** method to see location and live bed availability influence the rank."
        )
    else:
        lines.append(
            f"Using **BedScore (recommended)** from {location}: "
            f"**{h1.get('name', '?')}** ranks #1 "
            f"(Score = 100 · P · [0.35·Trust + 0.40·Closeness + 0.25·Affordability]). "
            f"Distance: {h1.get('distance', '?')} km, Fee: Rs {h1.get('fee', '?')}/day, "
            f"Rating: {h1.get('rating', '?')}★, arrival bed chance: {h1.get('availability', '?')} "
            f"with {h1.get('beds_free', '?')} beds free now."
        )
        lines.append("")
        lines.append(
            "BedScore balances reputation trust, travel closeness, and affordability, "
            "multiplying by arrival bed probability P so low-bed hospitals drop in rank."
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


# ── Strict Number Verification Check ───────────────────────────────────
def post_check_numbers(response: str, facts: dict) -> bool:
    """Verify that every number in the LLM response appears in the input facts.
    
    Prevents hallucinated bed counts, distances, fees, and ratings.
    Allows only standard rank numbers (1..3), formula weights (25, 35, 40, 100),
    and verified emergency numbers (108, 112).
    """
    facts_str = json.dumps(facts)
    numbers_in_response = set(re.findall(r'\b\d+(?:\.\d+)?\b', response))
    numbers_in_facts = set(re.findall(r'\b\d+(?:\.\d+)?\b', facts_str))
    allowed_structural = {
        '0', '1', '2', '3', '100', '108', '112',
        '25', '35', '40', '0.25', '0.35', '0.40', '0.20', '0.30'
    }
    suspicious = numbers_in_response - numbers_in_facts - allowed_structural
    return len(suspicious) == 0


def _call_groq(facts: dict, language: str) -> str | None:
    """Call Groq API directly without langchain-groq."""
    try:
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            return None
        client = Groq(api_key=api_key, timeout=LLM_TIMEOUT)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(language=language)},
                {"role": "user", "content": f"Facts:\n{json.dumps(facts, indent=2)}"},
            ],
            max_tokens=300,
            temperature=0.2,
        )
        return response.choices[0].message.content
    except Exception:
        return None


def explain(facts: dict, language: str = "en") -> str:
    """Generate a plain-language explanation of the ranking.
    
    Tries configured LLM provider (Groq) with timeout.
    Validates numbers via post_check_numbers before returning.
    Falls back to deterministic template on any failure.
    """
    key = _hash_facts(facts) + language
    if key in _cache:
        return _cache[key]

    result = None

    if LLM_PROVIDER == "groq":
        result = _call_groq(facts, language)

    # Validate numbers: discard hallucinated responses
    if result and not post_check_numbers(result, facts):
        result = None

    if result is None:
        result = _template_fallback(facts, language)

    _cache[key] = result
    return result
