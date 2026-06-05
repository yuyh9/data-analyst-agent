import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

RESULTS_PATH = Path("eval/results")

JUDGE_PROMPT = """You are evaluating the quality of an AI data analyst's answer.

Score the answer on this single dimension:
SPECIFICITY — Does the answer give specific numbers, names, or facts rather than vague statements?

Scoring rubric:
5 — Answer gives exact numbers/names with clear context. Fully specific.
4 — Answer gives specific numbers but missing minor context.
3 — Answer is partially specific — some numbers but also vague parts.
2 — Answer is mostly vague with only one specific detail.
1 — Answer is completely vague, no specific facts at all.

Question: {question}
Answer: {answer}

Respond with ONLY a JSON object in this exact format:
{{"score": <1-5>, "reason": "<one sentence explanation>"}}"""


def judge_answer(question: str, answer: str) -> dict:
    """Score a single answer using GPT-4o-mini as judge."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": JUDGE_PROMPT.format(
                    question=question,
                    answer=answer
                )
            }
        ],
        temperature=0,
        timeout=30
    )
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def judge_answer_gpt4o(question: str, answer: str) -> dict:
    """Second judge using GPT-4o for kappa comparison."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": JUDGE_PROMPT.format(
                    question=question,
                    answer=answer
                )
            }
        ],
        temperature=0,
        timeout=30
    )
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def compute_cohens_kappa(ratings1: list[int], ratings2: list[int]) -> float:
    """
    Compute Cohen's kappa between two raters.
    Binarizes scores: >= 4 = positive, < 4 = negative.
    """
    assert len(ratings1) == len(ratings2), "Raters must score same number of items"
    n = len(ratings1)

    b1 = [1 if s >= 4 else 0 for s in ratings1]
    b2 = [1 if s >= 4 else 0 for s in ratings2]

    po = sum(1 for a, b in zip(b1, b2) if a == b) / n

    p1_pos = sum(b1) / n
    p2_pos = sum(b2) / n
    p1_neg = 1 - p1_pos
    p2_neg = 1 - p2_pos
    pe = (p1_pos * p2_pos) + (p1_neg * p2_neg)

    if pe == 1.0:
        return 1.0

    kappa = (po - pe) / (1 - pe)
    return round(kappa, 3)


def run_judge(results_file: str = "baseline_v2"):
    """Load eval results, score each answer with LLM judge."""
    results_path = RESULTS_PATH / f"{results_file}.json"
    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        return

    with open(results_path) as f:
        data = json.load(f)

    cases = data["cases"]
    print(f"Judging {len(cases)} answers from {results_file}...")
    print("=" * 50)

    judge_results = []
    scores = []

    for i, case in enumerate(cases):
        question = case["input"]
        answer = case.get("answer", "")

        if not answer:
            print(f"[{i+1}] {case['id']}: SKIP (no answer)")
            continue

        try:
            result = judge_answer(question, answer)
            score = result["score"]
            reason = result["reason"]
            scores.append(score)

            bar = "█" * score + "░" * (5 - score)
            print(f"[{i+1}] {case['id']}: {bar} {score}/5 — {reason[:70]}")

            judge_results.append({
                "id": case["id"],
                "input": question,
                "answer": answer[:200],
                "llm_score": score,
                "llm_reason": reason
            })

        except Exception as e:
            print(f"[{i+1}] {case['id']}: ERROR — {e}")

    avg_score = sum(scores) / len(scores) if scores else 0
    high_quality = sum(1 for s in scores if s >= 4)
    print(f"\n{'=' * 50}")
    print(f"Average score: {avg_score:.2f}/5")
    print(f"High quality (≥4): {high_quality}/{len(scores)} ({high_quality/len(scores)*100:.0f}%)")

    output = {
        "results_file": results_file,
        "average_score": avg_score,
        "high_quality_count": high_quality,
        "total": len(scores),
        "scores": scores,
        "cases": judge_results
    }
    output_path = RESULTS_PATH / f"judge_{results_file}.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Judge results saved to {output_path}")
    return output


def run_kappa_check(results_file: str = "baseline_v2"):
    """Run 10 cases through both judges and compute kappa."""
    results_path = RESULTS_PATH / f"{results_file}.json"
    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        return

    with open(results_path) as f:
        data = json.load(f)

    cases = data["cases"][:10]
    print("Running kappa check — GPT-4o-mini vs GPT-4o on 10 cases...")
    print("=" * 50)

    mini_scores = []
    gpt4o_scores = []

    for i, case in enumerate(cases):
        question = case["input"]
        answer = case.get("answer", "")
        if not answer:
            continue

        s1 = judge_answer(question, answer)["score"]
        s2 = judge_answer_gpt4o(question, answer)["score"]
        mini_scores.append(s1)
        gpt4o_scores.append(s2)

        match = "✅" if s1 == s2 else "⚠️ "
        print(f"{match} {case['id']}: mini={s1}  gpt4o={s2}  {'agree' if s1==s2 else 'disagree'}")

    kappa = compute_cohens_kappa(mini_scores, gpt4o_scores)

    print(f"\n{'=' * 50}")
    print(f"GPT-4o-mini scores: {mini_scores}")
    print(f"GPT-4o      scores: {gpt4o_scores}")
    print(f"Cohen's kappa:      {kappa}")
    print(f"Target:             >= 0.6")

    if kappa >= 0.8:
        interpretation = "Almost perfect agreement"
    elif kappa >= 0.6:
        interpretation = "Substantial agreement ✅ meets requirement"
    elif kappa >= 0.4:
        interpretation = "Moderate agreement — below target"
    else:
        interpretation = "Fair/poor agreement — consider revising judge prompt"

    print(f"Interpretation:     {interpretation}")

    output = {
        "judge_1": "gpt-4o-mini",
        "judge_2": "gpt-4o",
        "mini_scores": mini_scores,
        "gpt4o_scores": gpt4o_scores,
        "kappa": kappa,
        "interpretation": interpretation
    }
    with open(RESULTS_PATH / "kappa_result.json", "w") as f:
        json.dump(output, f, indent=2)
    print("Saved to eval/results/kappa_result.json")
    return output


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kappa":
        run_kappa_check()
    else:
        results_file = sys.argv[1] if len(sys.argv) > 1 else "baseline_v2"
        run_judge(results_file)