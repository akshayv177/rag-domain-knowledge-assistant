"""
eval_label.py — Interactive labeling tool for RAG eval runs (v0)

Purpose
-------
Turn raw eval-run logs (JSONL) into human-labeled datasets that help you:
- audit retrieval quality vs answer quality
- bucket failures into actionable categories
- track progress over time as you change chunking/retrieval/prompting

Input format (eval runs)
------------------------
Reads a JSONL file produced by `scripts/eval_run.py`, where each line is a JSON
object containing (at minimum):

- eval_id: str                Stable id for the eval question
- query: str                  User query
- expected_answer: str        Gold answer text (may be empty in v0)
- answer: str                 Model output
- retrieved: List[{
    rank: int,
    source: str,
    score: float|None,
    snippet: str
  }]
- answer_label: str           Placeholder (often "unlabeled")
- retrieval_label: str        Placeholder (often "unlabeled")

Output format (labeled runs)
----------------------------
Writes a new JSONL file under `data/logs/eval_runs_labeled/` (or `--out`) where
each line is the original record plus labeling fields:

- answer_label: "correct" | "partial" | "wrong" | "oos"
- retrieval_label: "ok" | "bad"
- failure_bucket: one of FAILURE_BUCKETS
- label_notes: str            Optional free-form notes
- labeled_at: str             Timestamp when labeling was applied

Operational notes
-----------------
- Default input is the latest `.jsonl` under `data/logs/eval_runs/` if `--in`
  is not provided.
- Safe to re-run: records already labeled (non-"unlabeled") are skipped.
- Labels are intentionally manual-first in v0. Once you have enough labeled
  examples, you can build a lightweight auto-grader or use an LLM-as-judge
  workflow (later).

Usage
-----
  PYTHONPATH=src python scripts/eval_label.py --limit 5
  PYTHONPATH=src python scripts/eval_label.py --in data/logs/eval_runs/2026-01-19.jsonl --limit 5
  PYTHONPATH=src python scripts/eval_label.py --limit 5 --start 5

"""

import argparse, json
from datetime import datetime
from pathlib import Path

ANSWER_LABELS = ["correct", "partial", "wrong", "oos"]
RETRIEVAL_LABELS = ["ok", "bad"]

FAILURE_BUCKETS = [
    "retrieval_miss",
    "chunking_issue",
    "grounding_failure",
    "instruction_following",
    "ambiguity_handling",
    "formatting",
    "other",
]

def _latest_jsonl(dirpath: Path) -> Path:
    """
    Return the most recently modified `.jsonl` file in a directory.

    Used to automatically pick the latest eval run output when the user
    doesn't explicitly pass `--in`.

    Args:
        dirpath: Directory containing JSONL eval run files.

    Returns:
        Path to the newest `.jsonl` file by modification time.

    Raises:
        FileNotFoundError: If the directory contains no `.jsonl` files.
    """

    files = sorted(dirpath.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files: raise FileNotFoundError(f"No .jsonl files found in {dirpath}")
    return files[0]

def _preview(s: str, n: int = 400) -> str:
    """
    Produce a compact, single-line preview of a longer text blob.

    This keeps the interactive labeling UI readable by:
    - stripping leading/trailing whitespace
    - replacing newlines with spaces
    - truncating to `n` characters and adding "..." when needed

    Args:
        s: Input text (may be empty/None-like).
        n: Maximum number of characters to return.

    Returns:
        A cleaned, truncated preview string.
    """
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[:n] + "..."

def _prompt_choice(prompt: str, choices: list[str], default: str | None = None) -> str:
    """
    Prompt the user to select a value from a fixed set of choices.

    Intended for labeling fields where we want consistent categories
    (e.g., answer_label, retrieval_label, failure_bucket).

    The prompt will repeat until the user enters a valid choice.
    If the user submits an empty input and a default is provided, the
    default is returned.

    Args:
        prompt: Human-readable prompt label (e.g., "answer_label").
        choices: Allowed values.
        default: Optional default value returned on empty input.

    Returns:
        The selected choice (always one of `choices`).
    """

    choices_str = "/".join(choices)
    while True:
        suffix = f"[{choices_str}]"
        if default: suffix += f"(default={default})"
        x = input(prompt + suffix + ": ").strip().lower()
        if x in choices: return x
        print(f"Invalid. Choose one of {choices_str}")

def _prompt_free(prompt: str) -> str:
    """
    Prompt the user for optional free-form text.

    Used for quick human notes during labeling, e.g., why a response was
    considered partial or what went wrong.

    Args:
        prompt: The prompt text (e.g., "notes").

    Returns:
        The user's input string (may be empty).
    """

    return input(prompt + " (optional): ").strip()

def main():
    """
    Interactive labeling CLI for RAG eval runs.

    This script:
    1) Loads an input JSONL eval run file (defaults to the latest file in
       `data/logs/eval_runs/` if `--in` is not provided).
    2) Iterates through eval records and displays:
       - query
       - expected answer (if present)
       - model answer
       - top retrieved chunks (source/score/snippet)
    3) Prompts the user to apply labels:
       - answer_label: correct/partial/wrong/oos
       - retrieval_label: ok/bad
       - failure_bucket: predefined bucket list
       - optional notes
    4) Writes labeled records to a new JSONL output file:
       - default: `data/logs/eval_runs_labeled/YYYY-MM-DD.labeled.jsonl`
       - or user-provided via `--out`

    Notes / behavior:
    - Minimal mutation: only adds labeling-related fields.
    - Safe to re-run: records that already have non-"unlabeled" labels
      are skipped.
    - Prints a summary over the labeled output file at the end.

    CLI args:
        --in: input eval JSONL path (optional)
        --out: output labeled JSONL path (optional)
        --limit: number of records to label in this run (default 5)
        --start: starting line index in the input file (default 0)
    """

    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", default="", help="Path to eval JSONL. If empty, uses latest in data/logs/eva_runs/")
    ap.add_argument("--out", dest="out_path", default="", help="Output labeled JSONL path. If empty, uses data/logs/eval_runs_labeled/<date>.labeled.jsonl")
    ap.add_argument("--limit", type=int, default=5, help="How many items to label this run")
    ap.add_argument("--start", type=int, default=0, help="Start index (0-based) within file lines")
    args = ap.parse_args()

    in_dir = Path("data/logs/eval_runs")
    in_path = Path(args.in_path) if args.in_path else _latest_jsonl(in_dir)

    lines = in_path.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(x) for x in lines if x.strip()]

    # default output path
    if args.out_path:
        out_path = Path(args.out_path)
    else:
        out_dir = Path("data/logs/eval_runs_labeled")
        out_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().date().isoformat()
        out_path = out_dir / f"{date_str}.labeled.jsonl"

    print(f"\nInput: {in_path} ({len(rows)} rows)")
    print(f"Output: {out_path}")
    print(f"Labeling limit: {args.limit}, starting at index: {args.start}\n")

    labeled = 0
    out_f = out_path.open("a", encoding="utf-8")

    try:
        for i in range(args.start, len(rows)):
            if labeled > args.limit: break
            r = rows[i]

            # skip already labeled if you re-run
            if r. get("answer_label") not in (None, "", "unlabeled") and r.get("retrieval_label") not in ("None", "unlabeled"):
                continue

            print("=" * 50)
            print(f"[{i}] eval_id={r.get('eval_id','')} top_k={r.get('top_k','')}")
            print(f"Query: {r.get('query','')}\n")
            if r.get("expected_answer") is not None:
                print("Expected: ")
                print(_preview(r.get("expected_answer",""), 600), "\n")

            print("Answer:")
            print(_preview(r.get("expected_answer",""), 900), "\n")

            retrieved = r.get("retrieved",[]) or []
            for it in retrieved[:3]:
                print(f"    - score={it.get('score')} source={it.get('source')}")
                print(f"      { _preview(it.get('snippet'<''), 220) }")
            print("")

            ans_label = _prompt_choice("answer_label", ANSWER_LABELS, default="partial")
            ret_label = _prompt_choice("retrieval_label", RETRIEVAL_LABELS, default="ok")
            bucket = _prompt_choice("failure_bucket", FAILURE_BUCKETS, default="other")
            notes = _prompt_free("notes")

            r["answer_label"] = ans_label
            r["retrieval_label"] = ret_label
            r["failure_bucket"] = bucket
            r["label_notes"] = notes
            r["labeled_at"] = datetime.now().isoformat()

            out_f.write(json.dumps(r, ensure_ascii=False) + "\n")
            out_f.flush()
            labeled += 1
            print(f"Saved label {labeled}/{args.limit}\n")

    finally:
        out_f.close()

    # Summary output file
    out_rows = [json.loads(x) for x in out_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    def _count(key: str):
        c = {}
        for rr in out_rows:
            v = rr.get(key, "unlabeled") or "unlabeled"
            c[v] = c.get(v, 0) + 1
        return c
    
    print("\n=== Summary (labeled file) ===")
    print("answer_label: ", _count("answer_label"))
    print("retrieval_label: ", _count("retrieval_label"))
    print("failuire_bucket:", _count("failure_bucket"))
    print(f"Output file: {out_path}")

if __name__ == "__main__":
    main()