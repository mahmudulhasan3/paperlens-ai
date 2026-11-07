import json
import time

from evaluate_retrieval import is_relevant, QUESTION_FILE, EVAL_OWNER
from paperlens.indexing.vector_store import count_chunks
from paperlens.generation.answer import answer_baseline

RESULT_FILE = "evaluation/results_answers.json"
DETAIL_FILE = "evaluation/answers_detail.json"


# Evaluation step 3 (Run): answer every question with baseline RAG and measure citations, tokens and time
def main():
    if count_chunks(EVAL_OWNER) == 0:
        print("No evaluation chunks found. Run evaluate_retrieval.py first.")
        return

    with open(QUESTION_FILE) as f:
        all_questions = json.load(f)

    questions = []
    for item in all_questions:
        if item["answerable"]:
            questions.append(item)

    details = []
    precision_sum = 0.0
    recall_sum = 0.0
    token_sum = 0
    latency_sum = 0.0
    answered = 0
    wrongly_abstained = 0

    for item in questions:
        try:
            result = answer_baseline(item["question"], EVAL_OWNER, top_k=5)
        except Exception as error:
            print("Skipped", item["id"], ":", error)
            continue

        citations = result["citations"]
        relevant_cited = 0
        for citation in citations:
            if is_relevant(item, citation):
                relevant_cited = relevant_cited + 1

        precision = 0.0
        if len(citations) > 0:
            precision = relevant_cited / len(citations)

        recall = 0.0
        if relevant_cited > 0:
            recall = 1.0

        if result["abstained"]:
            wrongly_abstained = wrongly_abstained + 1
        else:
            answered = answered + 1
            precision_sum = precision_sum + precision
            recall_sum = recall_sum + recall

        token_sum = token_sum + result["prompt_tokens"] + result["output_tokens"]
        latency_sum = latency_sum + result["latency"]

        details.append(
            {
                "id": item["id"],
                "question": item["question"],
                "expected_answer": item["expected_answer"],
                "answer": result["answer"],
                "abstained": result["abstained"],
                "citation_precision": round(precision, 3),
                "citation_recall": recall,
            }
        )

        time.sleep(2)

    total = len(details)
    if total == 0:
        print("No answers were produced")
        return

    summary = {
        "questions": total,
        "wrongly_abstained": wrongly_abstained,
        "avg_citation_precision": round(precision_sum / max(answered, 1), 3),
        "avg_citation_recall": round(recall_sum / max(answered, 1), 3),
        "avg_tokens": round(token_sum / total),
        "avg_latency_seconds": round(latency_sum / total, 2),
    }

    print(summary)

    with open(RESULT_FILE, "w") as f:
        json.dump(summary, f, indent=2)
    with open(DETAIL_FILE, "w") as f:
        json.dump(details, f, indent=2)


if __name__ == "__main__":
    main()
