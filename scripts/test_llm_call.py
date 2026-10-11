"""Test script to execute LLM provider call with grounded data and save proof."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from src.config import LANDMARKS
from src.data import load_hospitals
from src.llm import build_facts, call_groq_detailed, explain, post_check_numbers
from src.scoring import rank_hospitals


def main():
    # 1. Load real hospitals dataset — NO hand-typed facts!
    hospitals = load_hospitals()
    location_name = "Bhubaneswar Railway Station"
    landmark = LANDMARKS.get(location_name, (20.2687, 85.8427))
    user_lat, user_lon = landmark[0], landmark[1]

    # 2. Run app's own ranking function on real dataframe
    method = "BedScore (recommended)"
    ranked = rank_hospitals(hospitals, user_lat, user_lon, method=method)

    # 3. Build grounded facts dictionary directly from dataframe
    input_facts = build_facts(ranked, method=method, location_name=location_name, top_n=3)

    print(f"Generated grounded input facts for {location_name} (Top 3 hospitals):")
    for h in input_facts["top_hospitals"]:
        print(f"  #{h['rank']} {h['name']} - Dist: {h['distance']}km, Fee: Rs{h['fee']}, "
              f"Rating: {h['rating']}, Free beds: {h['beds_free']}")

    # 4. Call Groq directly (key from environment, never printed)
    print("\nCalling Groq API...")
    result = call_groq_detailed(input_facts, language="en")
    raw_response = result.get("raw_response")
    provider = result.get("provider", "template_fallback")
    latency_ms = result.get("latency_ms", 0)
    model = result.get("model")
    num_passed = result.get("number_check_passed", False)

    if provider == "groq" and raw_response and num_passed:
        print(f"Groq API call succeeded using model '{model}' in {latency_ms}ms!")
        print(f"Number check: PASSED ({len(result.get('numbers_extracted', []))} numbers verified)")
        final_output = raw_response
    else:
        print(f"Provider: {provider} (model: {model}, latency: {latency_ms}ms, error: {result.get('error')})")
        print("Falling back to deterministic template...")
        final_output = explain(input_facts, "en")
        num_passed = post_check_numbers(final_output, input_facts)

    proof = {
        "provider": provider,
        "model": model,
        "latency_ms": latency_ms,
        "input_facts": input_facts,
        "raw_response": raw_response,
        "numbers_extracted": result.get("numbers_extracted", []),
        "allowed_numbers": result.get("allowed_numbers", []),
        "suspicious_numbers": result.get("suspicious_numbers", []),
        "number_check_passed": num_passed,
        "final_output": final_output,
        "code_lines_highlight": {
            "post_check_numbers": "src/llm.py:114-131",
            "call_groq_detailed": "src/llm.py:157-227",
            "build_facts": "src/llm.py:89-111",
        }
    }

    out_file = Path("docs/llm_proof.json")
    out_file.write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print(f"\nSaved proof to {out_file}!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
