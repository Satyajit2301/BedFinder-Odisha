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
from src.config import MENTOR_A_WEIGHT

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq" if os.getenv("GROQ_API_KEY") else "none").lower()
LLM_TIMEOUT = 8  # seconds timeout
_cache: dict[str, str] = {}

SYSTEM_PROMPT = """You are a hospital recommendation assistant for Bhubaneswar, Odisha.
Rules:
- Use ONLY the facts provided in the JSON. Never invent facts or numbers.
- Distinguish between 'bed_chance_on_arrival' (probability P of getting a bed after travel) and 'bed_availability_pct' (% of beds currently free).
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
            f"Using the mentor's formula `Score = {int(MENTOR_A_WEIGHT)}·A + X − Y − Z` "
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
            f"Rating: {h1.get('rating', '?')}★, arrival bed chance: {h1.get('bed_chance_on_arrival', '?')} "
            f"with {h1.get('beds_free', '?')} of {h1.get('beds_total', '?')} beds free ({h1.get('bed_availability_pct', '?')}% available)."
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


# ── Build Grounded Facts from Real DataFrame ───────────────────────────
def build_facts(df_ranked, method: str, location_name: str, top_n: int = 3) -> dict:
    """Build grounded input facts dictionary from ranked hospital DataFrame."""
    top_facts = []
    avail_col = "general_ward_available_beds" if "general_ward_available_beds" in df_ranked.columns else "beds_free_now"
    tot_col = "general_ward_total_beds" if "general_ward_total_beds" in df_ranked.columns else "general_beds"
    for _, r in df_ranked.head(top_n).iterrows():
        p_val = float(r.get("p_bed", 1.0))
        p_pct = f"{int(round(p_val * 100))}%"
        free_b = int(r[avail_col])
        tot_b = int(r[tot_col])
        avail_pct = round(100.0 * free_b / max(tot_b, 1), 1)
        top_facts.append({
            "name": str(r["hospital_name"]),
            "rank": int(r["rank"]),
            "score": round(float(r.get("score", 0)), 1),
            "distance": round(float(r["dist_km"]), 1),
            "fee": int(r["admission_fee_inr"]),
            "rating": round(float(r["rating_5"]), 1),
            "reviews": int(r["review_count"]),
            "bed_chance_on_arrival": p_pct,
            "beds_free": free_b,
            "beds_total": tot_b,
            "bed_availability_pct": avail_pct,
        })
    return {
        "method": method,
        "location_name": location_name,
        "top_hospitals": top_facts,
    }


# ── Strict Number Verification Check ───────────────────────────────────
def post_check_numbers(response: str, facts: dict) -> bool:
    """Verify that every number in the LLM response appears in the input facts.
    
    Prevents hallucinated bed counts, distances, fees, and ratings.
    Allows only standard rank numbers (1..5), formula weights (20, 25, 35, 40, 100),
    and verified emergency numbers (108, 112).
    """
    facts_str = json.dumps(facts)
    numbers_in_response = set(re.findall(r'\b\d+(?:\.\d+)?\b', response))
    raw_facts_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', facts_str))
    int_parts = {n.split('.')[0] for n in raw_facts_nums if '.' in n}
    numbers_in_facts = raw_facts_nums | int_parts
    allowed_structural = {
        '0', '1', '2', '3', '4', '5', '10', '100', '108', '112',
        '20', '25', '30', '35', '40', '0.20', '0.25', '0.30', '0.35', '0.40'
    }
    suspicious = numbers_in_response - numbers_in_facts - allowed_structural
    return len(suspicious) == 0


def inspect_numbers(response: str, facts: dict) -> dict:
    """Return detailed breakdown of extracted vs allowed numbers."""
    facts_str = json.dumps(facts)
    numbers_in_response = set(re.findall(r'\b\d+(?:\.\d+)?\b', response))
    raw_facts_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', facts_str))
    int_parts = {n.split('.')[0] for n in raw_facts_nums if '.' in n}
    numbers_in_facts = raw_facts_nums | int_parts
    allowed_structural = {
        '0', '1', '2', '3', '4', '5', '10', '100', '108', '112',
        '20', '25', '30', '35', '40', '0.20', '0.25', '0.30', '0.35', '0.40'
    }
    allowed_all = numbers_in_facts | allowed_structural
    suspicious = numbers_in_response - allowed_all
    return {
        "numbers_in_response": sorted(list(numbers_in_response)),
        "allowed_numbers": sorted(list(allowed_all)),
        "suspicious_numbers": sorted(list(suspicious)),
        "passed": len(suspicious) == 0,
    }


def _call_groq(facts: dict, language: str) -> str | None:
    """Call Groq API directly, trying candidate models."""
    detail = call_groq_detailed(facts, language)
    return detail.get("raw_response")


def call_groq_detailed(facts: dict, language: str = "en") -> dict:
    """Call Groq API with timing and model fallback, returning detailed metrics."""
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return {
            "provider": "template_fallback",
            "model": None,
            "latency_ms": 0,
            "raw_response": None,
            "error": "Missing GROQ_API_KEY",
            "number_check_passed": False,
        }

    models_to_try = [
        os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile",
    ]
    # Remove duplicates preserving order
    candidates = list(dict.fromkeys([m for m in models_to_try if m]))

    t0 = time.time()
    last_err = None
    try:
        from groq import Groq
        client = Groq(api_key=api_key, timeout=LLM_TIMEOUT)

        for model in candidates:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT.format(language=language)},
                        {"role": "user", "content": f"Facts:\n{json.dumps(facts, indent=2)}"},
                    ],
                    max_tokens=300,
                    temperature=0.2,
                )
                latency_ms = int((time.time() - t0) * 1000)
                raw_text = response.choices[0].message.content or ""
                num_info = inspect_numbers(raw_text, facts)
                return {
                    "provider": "groq",
                    "model": model,
                    "latency_ms": latency_ms,
                    "raw_response": raw_text,
                    "numbers_extracted": num_info["numbers_in_response"],
                    "allowed_numbers": num_info["allowed_numbers"],
                    "number_check_passed": num_info["passed"],
                    "suspicious_numbers": num_info["suspicious_numbers"],
                }
            except Exception as e:
                last_err = str(e)
                continue

    except Exception as e:
        last_err = str(e)

    latency_ms = int((time.time() - t0) * 1000)
    return {
        "provider": "template_fallback",
        "model": None,
        "latency_ms": latency_ms,
        "raw_response": None,
        "error": last_err or "Unknown error",
        "number_check_passed": False,
    }


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

