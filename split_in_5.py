#!/usr/bin/env python3
"""
Split a "kept papers" JSON (a list of dicts) into 5 JSON files by relevance_score.

Input format: a JSON file containing a list like:
[
  {"paper_id": "...", "relevance_score": 5, ...},
  ...
]

Notes:
- Handles missing/invalid relevance_score by putting the entry into score=0 (optional) and reporting it.
- Keeps original entries unchanged.
- Stable-ish output ordering: sorts by (source_file, batch_id, paper_id) for readability.
"""

import argparse
import json
import os
from typing import Any, Dict, List, Tuple


def safe_int(x: Any) -> int:
    try:
        return int(x)
    except Exception:
        return -1


def sort_key(rec: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(rec.get("source_file") or ""),
        str(rec.get("batch_id") or ""),
        str(rec.get("paper_id") or rec.get("id") or ""),
    )


def load_list(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, list):
        raise ValueError(f"Expected a JSON list in {path}, got {type(obj)}")
    return obj


def write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_json", required=True, help="Input JSON file (list of papers).")
    ap.add_argument(
        "--out_dir",
        required=True,
        help="Output directory. Will write score_1.json ... score_5.json",
    )
    ap.add_argument(
        "--prefix",
        default="score_",
        help='Output filename prefix (default: "score_").',
    )
    ap.add_argument(
        "--keep_invalid",
        action="store_true",
        help="Also write invalid_score.json for entries with missing/invalid score.",
    )
    args = ap.parse_args()

    papers = load_list(args.in_json)
    papers.sort(key=sort_key)

    buckets: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(1, 6)}
    invalid: List[Dict[str, Any]] = []

    for rec in papers:
        s = safe_int(rec.get("relevance_score"))
        if s in buckets:
            buckets[s].append(rec)
        else:
            invalid.append(rec)

    # Write 5 JSONs
    for score in range(1, 6):
        out_path = os.path.join(args.out_dir, f"{args.prefix}{score}.json")
        write_json(out_path, buckets[score])
        print(f"Wrote {len(buckets[score])} entries -> {out_path}")

    if args.keep_invalid:
        out_path = os.path.join(args.out_dir, "invalid_score.json")
        write_json(out_path, invalid)
        print(f"Wrote {len(invalid)} invalid-score entries -> {out_path}")
    else:
        if invalid:
            print(f"Warning: {len(invalid)} entries had missing/invalid relevance_score and were skipped.")
            print("Tip: rerun with --keep_invalid to save them.")


if __name__ == "__main__":
    main()

    # python split_in_5.py   --in_json /home/jim/AI_papers/all_results/combined.json   --out_dir /home/jim/AI_papers/all_results/by_score 