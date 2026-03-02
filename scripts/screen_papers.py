#!/usr/bin/env python3
"""
scripts/screen_papers.py

Generic batch screener for conference paper JSON lists using an LLM.
- Prompt is external (text file) so you can swap policies (AI vs PL vs custom).
- Robust logging to JSONL (append/resume supported by default).
- Extract-only mode produces readable JSON/CSV from existing raw logs.

Prompt file must contain placeholders:
  {batch_id}
  {papers_block}

Usage examples:
  python3 scripts/screen_papers.py --prompt_file prompts/ai_se.txt \
    --inputs NEURIPS/neurips2025_cleaned.json --out_raw_jsonl logs/neurips2025.raw.jsonl \
    --extract_out_json logs/neurips2025.kept.json --extract_out_csv logs/neurips2025.kept.csv

  # resume (default): append + skip already-logged batch_ids
  python3 scripts/screen_papers.py --prompt_file prompts/pl_ai.txt \
    --inputs data/pacmpl10_popl.json --out_raw_jsonl logs/popl2026.raw.jsonl

  # extract-only
  python3 scripts/screen_papers.py --extract_only \
    --out_raw_jsonl logs/popl2026.raw.jsonl --extract_out_json logs/popl2026.kept.json
"""

import argparse
import csv
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Set

from openai import OpenAI


# ----------------------------
# utils: IO
# ----------------------------

def load_json_list(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, list):
        raise ValueError(f"Expected a JSON list in {path}, got {type(obj)}")
    return obj


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_existing_batch_ids(raw_jsonl_path: str) -> Set[str]:
    existing: Set[str] = set()
    if not os.path.exists(raw_jsonl_path):
        return existing
    with open(raw_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                bid = rec.get("batch_id")
                if bid:
                    existing.add(str(bid))
            except Exception:
                # ignore malformed lines
                pass
    return existing


# ----------------------------
# prompt formatting
# ----------------------------

def normalize_keywords(kw: Any) -> Optional[str]:
    if kw is None:
        return None
    if isinstance(kw, list):
        parts = [str(x).strip() for x in kw if str(x).strip()]
        return "; ".join(parts) if parts else None
    if isinstance(kw, str):
        s = kw.strip()
        return s if s else None
    return None


def truncate(text: Optional[str], max_chars: int) -> str:
    if not text:
        return ""
    t = " ".join(str(text).split())
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 3] + "..."


def make_papers_block(papers: List[Dict[str, Any]], abs_max_chars: int) -> str:
    lines: List[str] = []
    for i, p in enumerate(papers, start=1):
        paper_id = p.get("id") or p.get("paper_id") or p.get("forum") or f"paper_{i}"
        title = truncate(p.get("title"), 300)
        abstract = truncate(p.get("abstract"), abs_max_chars)
        keywords = normalize_keywords(p.get("keywords"))

        lines.append(f"{i}) [paper_id={paper_id}] Title: {title}")
        lines.append(f"   Keywords: {keywords if keywords else '(none)'}")
        lines.append(f"   Abstract: {abstract}")
        lines.append("")
    return "\n".join(lines).strip()


def chunked(lst: List[Any], n: int) -> List[List[Any]]:
    return [lst[i:i + n] for i in range(0, len(lst), n)]


# ----------------------------
# parsing / extraction
# ----------------------------

def try_parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    s = text.strip()

    if s.startswith("{") and s.endswith("}"):
        try:
            return json.loads(s)
        except Exception:
            pass

    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if not m:
        return None
    candidate = m.group(0).strip()
    try:
        return json.loads(candidate)
    except Exception:
        return None


def extract_results_from_raw_jsonl(
    raw_jsonl_path: str,
    out_json_path: str,
    out_csv_path: Optional[str] = None,
) -> Dict[str, Any]:
    kept_rows: List[Dict[str, Any]] = []
    batches_total = 0
    batches_with_kept = 0
    parse_failures = 0

    with open(raw_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            batches_total += 1
            rec = json.loads(line)

            batch_id = rec.get("batch_id")
            raw = rec.get("raw_response", "")
            parsed = try_parse_json_object(raw)

            if parsed is None:
                parse_failures += 1
                continue

            kept = parsed.get("kept")
            if not kept:
                continue

            batches_with_kept += 1

            prompt = rec.get("prompt", "")
            id_to_title: Dict[str, str] = {}
            for m in re.finditer(r"\[paper_id=(?P<pid>[^\]]+)\]\s+Title:\s+(?P<title>.*)", prompt):
                pid = m.group("pid").strip()
                title = m.group("title").strip()
                if pid and title:
                    id_to_title[pid] = title

            for item in kept:
                pid = item.get("paper_id")
                kept_rows.append({
                    "batch_id": batch_id,
                    "paper_id": pid,
                    "title": id_to_title.get(pid, ""),
                    "relevance_score": item.get("relevance_score"),
                    "reason": item.get("reason", ""),
                    "tags": item.get("tags", []),
                })

    kept_rows.sort(key=lambda r: (r.get("relevance_score") or 0, r.get("paper_id") or ""), reverse=True)

    summary = {
        "raw_jsonl": raw_jsonl_path,
        "batches_total": batches_total,
        "batches_with_kept": batches_with_kept,
        "parse_failures": parse_failures,
        "kept_total": len(kept_rows),
        "kept": kept_rows,
    }

    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    if out_csv_path:
        with open(out_csv_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["batch_id", "paper_id", "title", "relevance_score", "reason", "tags"],
            )
            w.writeheader()
            for r in kept_rows:
                row = dict(r)
                if isinstance(row.get("tags"), list):
                    row["tags"] = ";".join(row["tags"])
                w.writerow(row)

    return summary


# ----------------------------
# model call
# ----------------------------

def call_model(client: OpenAI, model: str, prompt: str) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


# ----------------------------
# main
# ----------------------------

def main() -> None:
    ap = argparse.ArgumentParser()

    ap.add_argument("--prompt_file", default="", help="Path to prompt template text file.")
    ap.add_argument("--inputs", nargs="+", default=[], help="One or more cleaned JSON files (lists of papers).")
    ap.add_argument("--out_raw_jsonl", required=True, help="Where to write raw batch results (JSONL).")

    ap.add_argument("--model", default="deepseek-reasoner")
    ap.add_argument("--base_url", default="https://api.openai-proxy.org/v1")
    ap.add_argument("--batch_size", type=int, default=10)
    ap.add_argument("--abs_max_chars", type=int, default=2000)
    ap.add_argument("--sleep_s", type=float, default=0.0)
    ap.add_argument("--max_batches", type=int, default=0, help="0 means run all batches.")

    ap.add_argument("--extract_out_json", default="")
    ap.add_argument("--extract_out_csv", default="")
    ap.add_argument("--extract_only", action="store_true")

    ap.add_argument("--overwrite_raw", action="store_true", help="Overwrite raw JSONL (default is resume/append).")

    args = ap.parse_args()

    # extract-only mode
    if args.extract_only:
        if not args.extract_out_json:
            raise ValueError("--extract_only requires --extract_out_json")
        extract_results_from_raw_jsonl(
            raw_jsonl_path=args.out_raw_jsonl,
            out_json_path=args.extract_out_json,
            out_csv_path=args.extract_out_csv or None,
        )
        return

    if not args.prompt_file:
        raise ValueError("--prompt_file is required unless --extract_only")
    if not args.inputs:
        raise ValueError("You must provide --inputs unless using --extract_only")

    prompt_template = read_text(args.prompt_file)
    if "{batch_id}" not in prompt_template or "{papers_block}" not in prompt_template:
        raise ValueError("Prompt template must contain placeholders: {batch_id} and {papers_block}")

    api_key = os.environ.get("CLOSE_API_KEY")
    if not api_key:
        raise ValueError("CLOSE_API_KEY is not set in environment.")

    client = OpenAI(base_url=args.base_url, api_key=api_key)

    # load and merge inputs
    papers: List[Dict[str, Any]] = []
    for path in args.inputs:
        papers.extend(load_json_list(path))
    papers = [p for p in papers if p.get("title") and p.get("abstract")]

    batches = chunked(papers, args.batch_size)
    os.makedirs(os.path.dirname(args.out_raw_jsonl) or ".", exist_ok=True)

    mode = "w" if args.overwrite_raw else "a"
    existing_batch_ids: Set[str] = set()
    if mode == "a":
        existing_batch_ids = load_existing_batch_ids(args.out_raw_jsonl)

    written = 0
    with open(args.out_raw_jsonl, mode, encoding="utf-8") as out:
        for bi, batch in enumerate(batches, start=1):
            if args.max_batches and bi > args.max_batches:
                break

            batch_id = f"batch_{bi:05d}"
            if mode == "a" and batch_id in existing_batch_ids:
                continue

            papers_block = make_papers_block(batch, args.abs_max_chars)
            prompt = (
                prompt_template
                    .replace("{batch_id}", batch_id)
                    .replace("{papers_block}", papers_block)
            )

            raw = call_model(client, args.model, prompt)

            record = {
                "batch_id": batch_id,
                "model": args.model,
                "prompt_file": args.prompt_file,
                "input_files": args.inputs,
                "paper_ids": [b.get("id") or b.get("paper_id") or b.get("forum") for b in batch],
                "prompt": prompt,
                "raw_response": raw,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            written += 1

            print(f"[{batch_id}] raw_len={len(raw)}")
            print(f"Processed batch {bi}/{len(batches)}: {len(batch)} papers (total written: {written})")
            #if a paper was selected then print the titles of the selected papers for quick feedback n the relevance score
            if args.sleep_s > 0:
                time.sleep(args.sleep_s)

    print(f"Done. Wrote {written} new batch records to {args.out_raw_jsonl}")

    if args.extract_out_json:
        extract_results_from_raw_jsonl(
            raw_jsonl_path=args.out_raw_jsonl,
            out_json_path=args.extract_out_json,
            out_csv_path=args.extract_out_csv or None,
        )
        print(f"Extracted results to: {args.extract_out_json}")


if __name__ == "__main__":
    main()