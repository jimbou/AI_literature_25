#!/usr/bin/env python3
"""
scripts/clean_papercopilot_json.py

General cleaner for PaperCopilot JSON dumps.

Goals:
- keep ONLY accepted papers (configurable)
- optionally restrict to certain tracks (e.g., main only)
- drop unwanted tracks (e.g., journal)
- output a normalized compact JSON list with fields:
  {id, title, abstract, keywords, track, status}

Examples
--------
# NeurIPS 2025 (accepted only; don't enforce track)
python3 scripts/clean_papercopilot_json.py \
  --in neurips2025.json --out neurips2025_cleaned.json

# ICLR 2025 (main track only + accepted statuses)
python3 scripts/clean_papercopilot_json.py \
  --in iclr2025.json --out iclr2025_cleaned.json \
  --require_track main \
  --accepted_statuses poster,spotlight,oral

# AAAI 2025 (drop journal track; keep anything else with title+abstract)
python3 scripts/clean_papercopilot_json.py \
  --in aaai2025.json --out aaai2025_cleaned.json \
  --drop_track_substrings journal \
  --accepted_statuses ""   # disables accepted filtering
"""

import argparse
import json
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_ACCEPTED = [
    "accept", "accepted",
    "oral", "spotlight", "poster",
]


def norm_str(x: Any) -> str:
    return str(x or "").strip()


def norm_lower(x: Any) -> str:
    return norm_str(x).lower()


def normalize_keywords(kw: Any) -> List[str]:
    if kw is None:
        return []
    if isinstance(kw, list):
        out = []
        for x in kw:
            s = norm_str(x)
            if s:
                out.append(s)
        return out
    if isinstance(kw, str):
        # PaperCopilot varies: commas/semicolons
        parts = kw.replace(",", ";").split(";")
        return [p.strip() for p in parts if p.strip()]
    return []


def pick_first(d: Dict[str, Any], keys: List[str]) -> Any:
    for k in keys:
        if k in d and d.get(k) is not None:
            return d.get(k)
    return None


def get_status(p: Dict[str, Any]) -> str:
    return norm_lower(pick_first(p, ["status", "decision", "final_decision", "result"]))


def get_track(p: Dict[str, Any]) -> str:
    return norm_lower(pick_first(p, ["track", "category", "area"]))


def get_id(p: Dict[str, Any]) -> str:
    # PaperCopilot varies by venue
    return norm_str(pick_first(p, ["id", "paper_id", "forum", "openreview_id", "pid"])) or ""


def get_keywords(p: Dict[str, Any]) -> List[str]:
    kw = pick_first(p, ["keywords", "keyword", "topics", "primary_area", "subject_areas"])
    return normalize_keywords(kw)


def parse_csv_set(s: str) -> List[str]:
    s = (s or "").strip()
    if not s:
        return []
    return [x.strip().lower() for x in s.split(",") if x.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Input PaperCopilot JSON file")
    ap.add_argument("--out", dest="out_path", required=True, help="Output cleaned JSON file")

    ap.add_argument(
        "--accepted_statuses",
        default=",".join(DEFAULT_ACCEPTED),
        help=("Comma-separated accepted statuses. "
              "Set to empty string to disable accepted-only filtering."),
    )

    ap.add_argument(
        "--require_track",
        default="",
        help=("If set, keep only papers whose track matches exactly "
              "(case-insensitive). Example: main"),
    )

    ap.add_argument(
        "--drop_track_substrings",
        default="",
        help=("Comma-separated substrings; drop papers whose track contains any. "
              "Example: journal,workshop"),
    )

    ap.add_argument(
        "--keep_fields",
        default="id,title,abstract,keywords,track,status",
        help="Comma-separated fields to keep in output.",
    )

    args = ap.parse_args()

    accepted = set(parse_csv_set(args.accepted_statuses))
    require_track = norm_lower(args.require_track)
    drop_subs = parse_csv_set(args.drop_track_substrings)
    keep_fields = [x.strip() for x in (args.keep_fields or "").split(",") if x.strip()]

    with open(args.in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise SystemExit("Input JSON must be a list of paper objects.")

    total = len(data)
    kept: List[Dict[str, Any]] = []

    dropped_no_title_abs = 0
    dropped_status = 0
    dropped_track = 0

    for p in data:
        if not isinstance(p, dict):
            continue

        title = p.get("title")
        abstract = p.get("abstract")
        if not title or not abstract:
            dropped_no_title_abs += 1
            continue

        track = get_track(p)
        status = get_status(p)

        # Drop track if it contains excluded substrings
        if drop_subs and any(sub in track for sub in drop_subs):
            dropped_track += 1
            continue

        # Require exact track
        if require_track and track != require_track:
            dropped_track += 1
            continue

        # Accepted-only filter (if enabled)
        if accepted:
            if status not in accepted:
                dropped_status += 1
                continue

        out_entry = {
            "id": get_id(p),
            "title": title,
            "abstract": abstract,
            "keywords": get_keywords(p),
            "track": norm_str(pick_first(p, ["track", "category", "area"])) or None,
            "status": norm_str(pick_first(p, ["status", "decision", "final_decision", "result"])) or None,
        }

        # Keep only requested fields (and drop Nones)
        filtered = {k: out_entry.get(k) for k in keep_fields if k in out_entry}
        filtered = {k: v for k, v in filtered.items() if v is not None}

        kept.append(filtered)

    with open(args.out_path, "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)

    print(f"Total papers in file: {total}")
    print(f"Kept: {len(kept)}")
    print(f"Dropped (missing title/abstract): {dropped_no_title_abs}")
    print(f"Dropped (track filter): {dropped_track}")
    print(f"Dropped (status filter): {dropped_status}")
    print(f"Wrote cleaned file to: {args.out_path}")


if __name__ == "__main__":
    main()