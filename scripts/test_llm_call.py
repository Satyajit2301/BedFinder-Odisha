"""Live proof script for LLM Smart Search (V9).

Sends 3 real sentences (English, Hindi, Hinglish) and saves:
- raw response
- parsed result
- validation status
- latency
to docs/llm_proof.json.
If no key/network, records provider 'rules' and notes live call not verified.
Never prints, logs, or commits any API key.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

from src.geo import load_gazetteer
from src.llm import clean_llm_json, parse_request, parse_request_rules, validate_parsed


def main():
    gaz_df = load_gazetteer()
    api_key = os.getenv("GROQ_API_KEY", "")

    test_sentences = [
        {
            "id": "english",
            "text": "Near Patia, I have an Ayushman card, cheapest first",
            "lang": "en",
        },
        {
            "id": "hindi",
            "text": "Patia ke paas, mere paas ayushman card hai, sabse sasta dikhao",
            "lang": "hi",
        },
        {
            "id": "hinglish",
            "text": "Near KIIT square, no card, top 5 hospitals nearest",
            "lang": "mixed",
        },
    ]

    results = []
    groq_client = None
    provider = "rules"

    if api_key:
        try:
            from groq import Groq
            groq_client = Groq(api_key=api_key, timeout=6.0)
            provider = "groq"
        except Exception as e:
            provider = "rules"

    all_ai = True
    for item in test_sentences:
        sentence = item["text"]
        t0 = time.time()
        raw_response = None
        parsed = None
        source = "rules"
        validation_status = "UNKNOWN"

        if groq_client is not None:
            models_to_try = [
                os.getenv("GROQ_MODEL"),
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                "qwen/qwen3.8-27b",
                "llama-3.3-70b-versatile",
            ]
            candidates = list(dict.fromkeys([m for m in models_to_try if m]))
            from src.llm import _build_system_prompt
            prompt = _build_system_prompt(gaz_df)
            call_ok = False
            last_err = None

            for model in candidates:
                try:
                    resp = groq_client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": sentence[:300]},
                        ],
                        max_tokens=150,
                        temperature=0.0,
                    )
                    raw_response = resp.choices[0].message.content or ""
                    cleaned = clean_llm_json(raw_response)
                    raw_json = json.loads(cleaned)
                    parsed, unk = validate_parsed(raw_json, gaz_df)
                    source = "AI"
                    validation_status = f"VALID ({model})"
                    call_ok = True
                    break
                except Exception as ex:
                    last_err = ex
                    continue

            if not call_ok:
                all_ai = False
                source = "rules"
                parsed, unk = parse_request_rules(sentence, gaz_df)
                validation_status = f"FALLBACK_RULES ({type(last_err).__name__ if last_err else 'Unknown'})"
        else:
            all_ai = False
            source = "rules"
            parsed, unk = parse_request_rules(sentence, gaz_df)
            validation_status = "RULES_ONLY (NO_API_KEY)"

        latency_ms = int((time.time() - t0) * 1000)

        results.append({
            "id": item["id"],
            "language": item["lang"],
            "input_text": sentence,
            "provider": source,
            "latency_ms": latency_ms,
            "raw_response": raw_response,
            "parsed_result": parsed,
            "validation_status": validation_status,
        })

    proof_doc = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
        "overall_provider": "groq" if (groq_client and all_ai) else "rules_fallback",
        "live_call_verified": bool(groq_client and all_ai),
        "results": results,
    }

    out_file = ROOT / "docs" / "llm_proof.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(proof_doc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(results)} test cases to {out_file}")
    for r in results:
        print(f"  [{r['id']}] Provider: {r['provider']}, Latency: {r['latency_ms']}ms, Place: {r['parsed_result']['place']}, Card: {r['parsed_result']['has_card']}, Sort: {r['parsed_result']['sort']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
