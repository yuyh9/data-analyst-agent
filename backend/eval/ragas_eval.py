import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import context_recall
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI
from agent.schema_rag import retrieve_relevant_schemas, build_schema_index
from dotenv import load_dotenv

load_dotenv()

# test cases with known required tables
RAGAS_CASES = [
    {
        "question": "Which product category has the most orders?",
        "ground_truth": "olist_order_items olist_products product_category_name_translation",
        "required_tables": ["olist_order_items", "olist_products"]
    },
    {
        "question": "What is the average review score per state?",
        "ground_truth": "olist_order_reviews olist_orders olist_customers",
        "required_tables": ["olist_order_reviews", "olist_customers"]
    },
    {
        "question": "Which payment type is most common?",
        "ground_truth": "olist_order_payments",
        "required_tables": ["olist_order_payments"]
    },
    {
        "question": "Top 5 sellers by total revenue",
        "ground_truth": "olist_order_items olist_sellers",
        "required_tables": ["olist_order_items", "olist_sellers"]
    },
    {
        "question": "How many orders were delivered late?",
        "ground_truth": "olist_orders",
        "required_tables": ["olist_orders"]
    },
    {
        "question": "Average freight cost by product category",
        "ground_truth": "olist_order_items olist_products product_category_name_translation",
        "required_tables": ["olist_order_items", "olist_products"]
    },
    {
        "question": "Which city has the most sellers?",
        "ground_truth": "olist_sellers",
        "required_tables": ["olist_sellers"]
    },
    {
        "question": "Monthly order count for 2017",
        "ground_truth": "olist_orders",
        "required_tables": ["olist_orders"]
    },
    {
        "question": "Average installments for credit card payments",
        "ground_truth": "olist_order_payments",
        "required_tables": ["olist_order_payments"]
    },
    {
        "question": "Which customers spent the most total?",
        "ground_truth": "olist_customers olist_orders olist_order_payments",
        "required_tables": ["olist_customers", "olist_order_payments"]
    },
]

def run_ragas_eval():
    print("Building schema index...")
    build_schema_index()

    print("Running RAG retrieval on test cases...")

    questions = []
    contexts = []
    ground_truths = []
    retrieval_results = []

    for case in RAGAS_CASES:
        schema_text, retrieved_tables = retrieve_relevant_schemas(
            case["question"], top_k=3
        )

        # check which required tables were retrieved
        hits = [t for t in case["required_tables"] if t in retrieved_tables]
        recall = len(hits) / len(case["required_tables"])

        retrieval_results.append({
            "question": case["question"],
            "required": case["required_tables"],
            "retrieved": retrieved_tables,
            "hits": hits,
            "recall": recall
        })

        questions.append(case["question"])
        contexts.append([schema_text])
        ground_truths.append(case["ground_truth"])

    # print manual recall results
    print("\n--- Manual Context Recall ---")
    total_recall = 0
    for r in retrieval_results:
        status = "✅" if r["recall"] == 1.0 else "⚠️ "
        print(f"{status} {r['question'][:55]}")
        print(f"   Required: {r['required']}")
        print(f"   Retrieved: {r['retrieved']}")
        print(f"   Recall: {r['recall']:.0%}")
        total_recall += r["recall"]

    avg_recall = total_recall / len(retrieval_results)
    print(f"\nAverage context recall: {avg_recall:.1%}")

    # run RAGAS context_recall
    print("\nRunning RAGAS evaluation...")
    try:
        llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))

        dataset = Dataset.from_dict({
            "question": questions,
            "contexts": contexts,
            "ground_truth": ground_truths,
        })

        result = evaluate(
            dataset,
            metrics=[context_recall],
            llm=llm
        )
        print(f"RAGAS context_recall: {result['context_recall']:.3f}")

        # save results
        os.makedirs("eval/results", exist_ok=True)
        output = {
            "manual_recall": avg_recall,
            "ragas_context_recall": result["context_recall"],
            "cases": retrieval_results
        }
        with open("eval/results/ragas_eval.json", "w") as f:
            json.dump(output, f, indent=2)
        print("Results saved to eval/results/ragas_eval.json")

    except Exception as e:
        print(f"RAGAS scoring error: {e}")
        print("Manual recall score is still valid for your eval.")

if __name__ == "__main__":
    run_ragas_eval()