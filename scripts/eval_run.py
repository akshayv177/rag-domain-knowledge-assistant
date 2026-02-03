import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

from rag_assistant.retrieval import answer

# v0 eval set: 10 questions with expected answers
# Each item has:
# -id: stable identifier for this eval question
# -query: the question we send to answer()
# -expected_answer: "gold" text for future grading/ manual comparison

EVAL_ITEMS = [
    {
        "id": "q1_satellite_count_direct",
        "query": "In the pre-flight check, how many satellites should the GPS lock on to?",
        "expected_answer": "In the pre-flight check, the GPS should lock on to at least 10 satellites.",
    },
    {
        "id": "q2_satellite_count_paraphrased",
        "query": "Is there a minumum number of satellites that the GPS should lock on to during pre-flight checks?",
        "expected_answer": "Yes, in the pre-flight checks, the GPS should lock on to at least 10 satellites before takeoff.",
    },
    {
        "id": "q3_baterry_inspection_procedure",
        "query": "How should the pilot inspect the battery during pre-flight checks?",
        "expected_answer": (
                    "The pilot should verify that all flight batteries are physically intact, with no swelling, dents, or visible leakage; "
            "confirm battery voltage is within the recommended range (22.2–25.0 V for a 6S pack); and ensure connectors are clean "
            "and firmly seated in the power distribution harness."
            ),
    },
    {
        "id": "q4_home_point_vs_failsafe",
        "query": "Should the pilot confirm whether the home point has been correctly recorded in the Ground Control Station during the failsafe tests?",
        "expected_answer": "The pilot should confirm that the home point has been correctly recorded in the GCS during the GPS and home point pre-flight checks, which should happen before the failsafe tests",
    },
    {
        "id": "q5_definition_example_preflight",
        "query": "What is a pre-flight check and give one example from our docs?",
        "expected_answer": (
            "Pre-flight checks are a list of things that a pilot should check before takeoff to ensure safe flight. "
            "For example, the pilot should verify that all flight batteries are intact, with no swellings, dents, or visible leakage "
            "as part of the battery inspection pre-flight checks."
            ),
    },
    {
        "id": "q6_out_of_scope_cheetah_speed",
        "query": "How fast can cheetahs run?", 
        "expected_answer": "Answer not in knowledge documents",
    },
    {
        "id": "q7_ambiguous_motor_vs_gps_order",
        "query": "Should the motor test be done before or after the GPS checks?",
        "expected_answer": "The motor test should be done after the pre-flight GPS checks",
    },
    {
        "id": "q8_list_preflight_checks",
        "query": "What are the different types of pre-flight checks a pilot should do before flight?",
        "expected_answer": (
            "A pilot should do the following pre-flight checks before takeoff: "
            "battery inspection, GPS and home point lock, control surface and motor test, and failsafe behaviour"
        ),
    },
    {
        "id": "q9_shorthand_bat_inspect",
        "query": "What happens in the bat inspec part of the pre-flight check?",
        "expected_answer": (
            "The pilot should verify that all flight batteries are physically intact, with no swelling, dents, or visible leakage; "
            "confirm battery voltage is within the recommended range (22.2-25.0 V for a 6S pack); and ensure connectors are clean "
            "and firmly seated in the power distribution harness"
        ),
    },
    {
        "id": "q10_tricky_negative_satellite_count",
        "query": "Should the pilot proceed with takeoff if the GPS is locked on to 8 satellites?",
        "expected_answer": "No, the pilot should wait until the GPS has locked on to at least 10 satellites before takeoff and ensure all other pre-flight checks are complete"
    },
]


def _utc_iso_now() -> str:
    """
    Return the current UTC time as an ISO 8601 string.
    Used for timestamping eval runs and individual queries
    """
    return datetime.now(timezone.utc).isoformat()


def _get_log_path(run_id: str) -> Path:
    """
    Compute and create (if needed) the log file path for this eval run.

    Logs are written to:
        data/logs/eval_runs/YYYY-MM-DD__<run_id_short>.jsonl

    This prevents accidental duplication when you run eval multiple times
    in the same day, because each run gets its own file.
    """
    base = Path("data/logs/eval_runs")
    base.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()  # YYYY-MM-DD
    run_id_short = run_id.replace(":", "").replace("-", "").replace(".", "")
    return base / f"{today}__{run_id_short}.jsonl"


# Core eval runner
def run_eval(top_k: int = 5, max_output_tokens: int = 400) -> Path:
    """
    Run the eval set against the current RAG answer() implementation.
    For each eval item, this function:
        - calls answer(query)
        - measures latency
        - shapes a JSON record with:
            run_date, run_id, eval_id, query, expected_answer, timestamp, 
            top_k, latency_s, answer, retrieved chunks, answer_label (placeholder),
            retrieval_label (placeholder)
        - appends the record to today's JSON log file
    
    It also prints a simple summary with counts of labels (currently all 'unlabeled').
    """
    
    run_id = _utc_iso_now()
    log_path = _get_log_path(run_id)

    # Simple label counters - all 'unlabeled' for v0, but structure is ready
    answer_label_counts: Dict[str, int] = {
        "correct": 0,
        "partial": 0,
        "wrong": 0,
        "oos": 0,
        "unlabeled": 0,
    }
    retrieval_label_counts: Dict[str, int] = {
        "ok": 0,
        "bad": 0,
        "unlabeled": 0,
    }

    print(f"Running eval run with {len(EVAL_ITEMS)} questions...")
    print(f"Logging to: {log_path}")

    with log_path.open("w", encoding="utf-8") as f:
        for idx, item in enumerate(EVAL_ITEMS):
            eval_id = item["id"]
            query = item["query"].strip()
            expected_answer = item["expected_answer"]

            if not query:
                continue

            # Measure end-to-end answer() latency
            t_start = time.perf_counter()
            result = answer(query, k_ctx=top_k, max_output_tokens=max_output_tokens)
            t_end = time.perf_counter()
            latency_s = t_end - t_start

            # answer() already returns a structured payload
            sources = result.get("sources", []) or []
            answer_text = result.get("answer", "")

            # v0 labels - these will be manually/automatically updated later
            answer_label = "unlabeled"
            retrieval_label = "unlabeled"

            answer_label_counts[answer_label] = answer_label_counts.get(answer_label, 0) + 1
            retrieval_label_counts[retrieval_label] = retrieval_label_counts.get(retrieval_label, 0) + 1

            # Normalize retrieved items for logging
            retrieved_for_log = []
            for rank, src in enumerate(sources, start=1):
                retrieved_for_log.append(
                    {
                        "rank": rank,
                        "source": src.get("source", "unknown"),
                        "score": src.get("score", None),
                        "snippet": src.get("snippet", ""),
                    }
                )

            record = {
                "run_date": str(datetime.now(timezone.utc).date()),
                "run_id": run_id,
                "eval_id": eval_id,
                "index": idx,
                "query": query,
                "timestamp": _utc_iso_now(),
                "top_k": top_k,
                "latency_s": latency_s,
                "answer": answer_text,
                "expected_answer": expected_answer,
                "retrieved": retrieved_for_log,
                "answer_label": answer_label,
                "retrieval_label": retrieval_label,
            }

            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Summary print (labels are placeholders for now)
    total = len(EVAL_ITEMS)
    print("\n=== Eval summary (labels may be placeholders) ===")
    print(f"Total questions: {total}")
    print(
        "Answers - correct: {correct}, partial: {partial}, wrong: {wrong}, oos: {oos}, unlabeled: {unlabeled}".format(
            **answer_label_counts
        )
    )
    print(
        "Retrieval - ok: {ok}, bad: {bad}, unlabeled: {unlabeled}".format(
            **retrieval_label_counts
        )
    )
    print(f"Log file: {log_path}")

    return log_path


# CLI enterypoint
def main():
    """
    CLI entrypoint for running the eval harness.

    Usage:
        PYTHONPATH=src python scripts/eval_run.py

    This will:
        - run the eval set against answer()
        - write JSONL logs under data/logs/eval_runs/
        - print a brief summary to stdout
    """
    run_eval(top_k=5, max_output_tokens=400)



if __name__ == "__main__":
    main()
