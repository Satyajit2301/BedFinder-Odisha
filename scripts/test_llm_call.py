"""Test script to execute one real LLM provider call and save input/output proof."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.llm import _call_groq, post_check_numbers, explain


def main():
    sample_facts = {
        "method": "BedScore (recommended)",
        "location_name": "Bhubaneswar Railway Station",
        "top_hospitals": [
            {
                "name": "Neelachal Hospital Pvt. Ltd.",
                "rank": 1,
                "score": 82.4,
                "distance": 2.1,
                "fee": 600,
                "rating": 4.1,
                "reviews": 1240,
                "availability": "98%",
                "beds_free": 18,
            },
            {
                "name": "Sunshine Hospital",
                "rank": 2,
                "score": 79.1,
                "distance": 3.4,
                "fee": 750,
                "rating": 4.2,
                "reviews": 2100,
                "availability": "95%",
                "beds_free": 14,
            },
            {
                "name": "Shree Hospitals",
                "rank": 3,
                "score": 76.5,
                "distance": 4.0,
                "fee": 500,
                "rating": 4.0,
                "reviews": 890,
                "availability": "92%",
                "beds_free": 12,
            }
        ]
    }

    print("Executing LLM call with Groq...")
    raw_response = _call_groq(sample_facts, "en")
    used_fallback = False

    if raw_response is None:
        print("Groq provider call returned None (network/auth/quota limit). Testing explain() with deterministic template...")
        final_text = explain(sample_facts, "en")
        passed_number_check = post_check_numbers(final_text, sample_facts)
        used_fallback = True
    else:
        print("Groq API returned response successfully!")
        passed_number_check = post_check_numbers(raw_response, sample_facts)
        final_text = raw_response

    proof = {
        "provider": "groq" if not used_fallback else "template_fallback",
        "model": "llama-3.3-70b-versatile",
        "input_facts": sample_facts,
        "raw_response": raw_response,
        "final_output": final_text,
        "number_check_passed": passed_number_check,
        "code_lines_highlight": {
            "post_check_numbers": "src/llm.py:84-95",
            "direct_groq_client": "src/llm.py:98-117",
            "timeout_and_fallback": "src/llm.py:120-142",
        }
    }

    out_file = Path("docs/llm_proof.json")
    out_file.write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print(f"Saved proof to {out_file}!")
    print(f"Number check passed: {passed_number_check}")
    print("\n--- Output Preview ---")
    safe_text = final_text.encode("ascii", errors="replace").decode("ascii")
    print(safe_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
