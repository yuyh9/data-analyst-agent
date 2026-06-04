import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core import chat, initialize
from pathlib import Path

#GOLDEN_PATH = Path("eval/golden.jsonl")
GOLDEN_PATH = Path("eval/golden_v1.jsonl")
RESULTS_PATH = Path("eval/results")
RESULTS_PATH.mkdir(parents=True, exist_ok=True)

def load_golden_set() -> list[dict]:
    cases = []
    with open(GOLDEN_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases

def evaluate_answer(answer: str, expected_facts: list, forbidden_facts: list) -> dict:
    """Check if answer contains expected facts and no forbidden facts."""
    answer_lower = answer.lower()

    expected_hits = []
    expected_misses = []
    for fact in expected_facts:
        if str(fact).lower() in answer_lower:
            expected_hits.append(fact)
        else:
            expected_misses.append(fact)

    forbidden_hits = []
    for fact in forbidden_facts:
        if str(fact).lower() in answer_lower:
            forbidden_hits.append(fact)

    # pass if at least one expected fact found and no forbidden facts
    passed = (
        (len(expected_facts) == 0 or len(expected_hits) > 0)
        and len(forbidden_hits) == 0
    )

    return {
        "passed": passed,
        "expected_hits": expected_hits,
        "expected_misses": expected_misses,
        "forbidden_hits": forbidden_hits
    }

def run_eval(experiment_name: str = "baseline"):
    print(f"\nRunning eval: {experiment_name}")
    print("=" * 50)

    initialize()
    cases = load_golden_set()
    results = []
    passed = 0

    for i, case in enumerate(cases):
        print(f"[{i+1}/{len(cases)}] {case['id']}: {case['input'][:50]}...")

        try:
            response = chat(case["input"], session_id=f"eval_{case['id']}")
            answer = response["answer"]
            eval_result = evaluate_answer(
                answer,
                case["expected_facts"],
                case["forbidden_facts"]
            )

            status = "✅ PASS" if eval_result["passed"] else "❌ FAIL"
            print(f"   {status}")
            if not eval_result["passed"]:
                print(f"   Answer: {answer[:100]}")
                print(f"   Missing: {eval_result['expected_misses']}")
                print(f"   Forbidden hits: {eval_result['forbidden_hits']}")

            if eval_result["passed"]:
                passed += 1

            results.append({
                "id": case["id"],
                "input": case["input"],
                "tags": case["tags"],
                "answer": answer,
                "passed": eval_result["passed"],
                "expected_hits": eval_result["expected_hits"],
                "expected_misses": eval_result["expected_misses"],
                "forbidden_hits": eval_result["forbidden_hits"],
                "chart_filepath": response.get("chart_filepath"),
                "tables_used": response.get("tables_used", [])
            })

        except Exception as e:
            print(f"   💥 ERROR: {str(e)}")
            results.append({
                "id": case["id"],
                "input": case["input"],
                "tags": case["tags"],
                "answer": "",
                "passed": False,
                "error": str(e)
            })

    # summary
    total = len(cases)
    score = passed / total * 100
    print(f"\n{'=' * 50}")
    print(f"Result: {passed}/{total} passed ({score:.1f}%)")

    # breakdown by tag
    tag_stats = {}
    for r in results:
        for tag in r.get("tags", []):
            if tag not in tag_stats:
                tag_stats[tag] = {"passed": 0, "total": 0}
            tag_stats[tag]["total"] += 1
            if r["passed"]:
                tag_stats[tag]["passed"] += 1

    print("\nBy tag:")
    for tag, stats in sorted(tag_stats.items()):
        pct = stats["passed"] / stats["total"] * 100
        print(f"  {tag}: {stats['passed']}/{stats['total']} ({pct:.0f}%)")

    # save results
    output = {
        "experiment": experiment_name,
        "score": score,
        "passed": passed,
        "total": total,
        "tag_stats": tag_stats,
        "cases": results
    }

    output_path = RESULTS_PATH / f"{experiment_name}.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")
    return output

if __name__ == "__main__":
    experiment = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    run_eval(experiment)