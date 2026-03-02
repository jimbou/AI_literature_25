#!/usr/bin/env python3
"""
Compare two "kept papers" JSON files (lists of dicts) and summarize differences.

Typical use:
- OLD = results with previous prompt criteria
- NEW = results with updated prompt criteria

Outputs:
- Newly kept papers (added)
- Papers no longer kept (dropped)
- Papers kept in both but with relevance_score changes (changed)
- Optional unchanged (same score)

Assumptions:
- Each entry has a stable id in one of: paper_id, id, forum (fallback to title hash-ish if needed)
- Each entry may have: title, relevance_score, reason, tags, source_file, batch_id

Notes:
- If multiple entries share the same id within a file, we keep the "best" one by:
  higher relevance_score, then longer reason, then first seen.
"""

import argparse
import json
import os
from typing import Any, Dict, List, Optional, Tuple


def safe_int(x: Any, default: int = -1) -> int:
    try:
        return int(x)
    except Exception:
        return default


def get_pid(rec: Dict[str, Any]) -> str:
    pid = rec.get("paper_id") or rec.get("id") or rec.get("forum")
    if pid:
        return str(pid).strip()

    # Fallback (only if you truly have no id): title-based key
    title = str(rec.get("title") or "").strip().lower()
    if title:
        return f"title:{title}"
    return ""


def choose_better(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pick better representative for same paper_id within the same file.
    """
    sa = safe_int(a.get("relevance_score"), default=-1)
    sb = safe_int(b.get("relevance_score"), default=-1)
    if sb > sa:
        return b
    if sa > sb:
        return a

    ra = str(a.get("reason") or "")
    rb = str(b.get("reason") or "")
    if len(rb) > len(ra):
        return b
    return a


def load_list(path: str, list_key: str = "") -> List[Dict[str, Any]]:
    """
    Accepts either:
      - a JSON list, or
      - a JSON dict containing a list under a key (default tries common keys).

    If --list_key is provided, use that key.
    """
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)

    if isinstance(obj, list):
        return obj

    if isinstance(obj, dict):
        if list_key:
            v = obj.get(list_key)
            if isinstance(v, list):
                return v
            raise ValueError(f"--list_key={list_key} not found or not a list in {path}")

        # Auto-detect common keys
        for k in ("kept", "papers", "items", "results", "data"):
            v = obj.get(k)
            if isinstance(v, list):
                return v

        raise ValueError(
            f"JSON in {path} is a dict but no list found under keys "
            f"kept/papers/items/results/data. Provide --list_key."
        )

    raise ValueError(f"Expected JSON list or dict in {path}, got {type(obj)}")


def index_by_pid(items: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Returns:
      mapping pid -> representative record
      invalid list (missing pid)
    """
    m: Dict[str, Dict[str, Any]] = {}
    invalid: List[Dict[str, Any]] = []
    for rec in items:
        pid = get_pid(rec)
        if not pid:
            invalid.append(rec)
            continue
        if pid not in m:
            m[pid] = rec
        else:
            m[pid] = choose_better(m[pid], rec)
    return m, invalid


def brief(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Small stable subset for reports.
    """
    return {
        "paper_id": get_pid(rec),
        "title": rec.get("title", ""),
        "relevance_score": rec.get("relevance_score"),
        "reason": rec.get("reason", ""),
        "tags": rec.get("tags", []),
        "source_file": rec.get("source_file", ""),
        "batch_id": rec.get("batch_id", ""),
    }


def write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def write_csv(path: str, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    import csv
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            out = dict(r)
            # Flatten tags if list
            if isinstance(out.get("tags_old"), list):
                out["tags_old"] = ";".join(out["tags_old"])
            if isinstance(out.get("tags_new"), list):
                out["tags_new"] = ";".join(out["tags_new"])
            w.writerow(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old_json", required=True, help="Old kept-papers JSON (list).")
    ap.add_argument("--new_json", required=True, help="New kept-papers JSON (list).")
    ap.add_argument("--out_json", required=True, help="Where to write the comparison report (JSON).")
    ap.add_argument("--out_csv", default="", help="Optional CSV with per-paper changes.")
    ap.add_argument("--include_unchanged", action="store_true", help="Include unchanged papers in report.")
    ap.add_argument("--top_k_examples", type=int, default=25, help="Include up to K examples per section.")
    ap.add_argument(
        "--list_key",
        default="",
        help="If input JSON is a dict, take the list from this key (e.g., kept). "
            "If empty, auto-detect common keys.",
    )
    args = ap.parse_args()

    old_items = load_list(args.old_json, list_key=args.list_key)
    new_items = load_list(args.new_json, list_key=args.list_key)

    old_map, old_invalid = index_by_pid(old_items)
    new_map, new_invalid = index_by_pid(new_items)

    old_ids = set(old_map.keys())
    new_ids = set(new_map.keys())

    added_ids = sorted(new_ids - old_ids)
    dropped_ids = sorted(old_ids - new_ids)
    common_ids = sorted(old_ids & new_ids)

    added: List[Dict[str, Any]] = [brief(new_map[pid]) for pid in added_ids]
    dropped: List[Dict[str, Any]] = [brief(old_map[pid]) for pid in dropped_ids]

    changed: List[Dict[str, Any]] = []
    unchanged: List[Dict[str, Any]] = []

    for pid in common_ids:
        o = old_map[pid]
        n = new_map[pid]
        so = safe_int(o.get("relevance_score"), default=-1)
        sn = safe_int(n.get("relevance_score"), default=-1)
        if so != sn:
            changed.append({
                "paper_id": pid,
                "title": n.get("title") or o.get("title") or "",
                "score_old": so,
                "score_new": sn,
                "delta": (sn - so) if (so != -1 and sn != -1) else None,
                "reason_old": o.get("reason", ""),
                "reason_new": n.get("reason", ""),
                "tags_old": o.get("tags", []),
                "tags_new": n.get("tags", []),
                "source_file_old": o.get("source_file", ""),
                "source_file_new": n.get("source_file", ""),
            })
        else:
            unchanged.append({
                "paper_id": pid,
                "title": n.get("title") or o.get("title") or "",
                "score": so,
                "reason": n.get("reason", "") or o.get("reason", ""),
                "tags": n.get("tags", []) or o.get("tags", []),
            })

    # Sort changed by largest absolute delta, then by new score desc
    def changed_key(x: Dict[str, Any]) -> Tuple[int, int, str]:
        d = x.get("delta")
        absd = abs(int(d)) if isinstance(d, int) else 0
        return (absd, safe_int(x.get("score_new"), default=-1), str(x.get("paper_id") or ""))

    changed.sort(key=changed_key, reverse=True)

    # Basic counts + score distribution shifts
    def score_hist(items: List[Dict[str, Any]], key: str = "relevance_score") -> Dict[str, int]:
        h = {str(i): 0 for i in range(1, 6)}
        h["invalid"] = 0
        for r in items:
            s = safe_int(r.get(key), default=-1)
            if 1 <= s <= 5:
                h[str(s)] += 1
            else:
                h["invalid"] += 1
        return h

    report = {
        "old_file": args.old_json,
        "new_file": args.new_json,
        "counts": {
            "old_total_unique": len(old_ids),
            "new_total_unique": len(new_ids),
            "added": len(added_ids),
            "dropped": len(dropped_ids),
            "score_changed": len(changed),
            "unchanged": len(unchanged),
            "old_missing_id": len(old_invalid),
            "new_missing_id": len(new_invalid),
        },
        "score_histograms": {
            "old": score_hist(list(old_map.values())),
            "new": score_hist(list(new_map.values())),
        },
        "added_examples": added[: args.top_k_examples],
        "dropped_examples": dropped[: args.top_k_examples],
        "changed_examples": changed[: args.top_k_examples],
    }

    if args.include_unchanged:
        report["unchanged_examples"] = unchanged[: args.top_k_examples]

    write_json(args.out_json, report)
    print(f"Wrote report -> {args.out_json}")

    if args.out_csv:
        rows = []
        # include all changed + added + dropped in CSV (useful)
        for x in changed:
            rows.append({
                "kind": "changed",
                "paper_id": x["paper_id"],
                "title": x["title"],
                "score_old": x["score_old"],
                "score_new": x["score_new"],
                "delta": x["delta"],
                "reason_old": x["reason_old"],
                "reason_new": x["reason_new"],
                "tags_old": x["tags_old"],
                "tags_new": x["tags_new"],
            })
        for x in added:
            rows.append({
                "kind": "added",
                "paper_id": x["paper_id"],
                "title": x["title"],
                "score_old": "",
                "score_new": x.get("relevance_score", ""),
                "delta": "",
                "reason_old": "",
                "reason_new": x.get("reason", ""),
                "tags_old": "",
                "tags_new": x.get("tags", []),
            })
        for x in dropped:
            rows.append({
                "kind": "dropped",
                "paper_id": x["paper_id"],
                "title": x["title"],
                "score_old": x.get("relevance_score", ""),
                "score_new": "",
                "delta": "",
                "reason_old": x.get("reason", ""),
                "reason_new": "",
                "tags_old": x.get("tags", []),
                "tags_new": "",
            })

        write_csv(
            args.out_csv,
            rows,
            fieldnames=[
                "kind",
                "paper_id",
                "title",
                "score_old",
                "score_new",
                "delta",
                "reason_old",
                "reason_new",
                "tags_old",
                "tags_new",
            ],
        )
        print(f"Wrote CSV -> {args.out_csv}")


if __name__ == "__main__":
    main()