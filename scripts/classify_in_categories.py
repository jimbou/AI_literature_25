import os
import json
import time
import argparse
from typing import Any, Dict, List, Optional, Tuple
import re
import csv
from openai import OpenAI


CATEGORIES = [
    "AGENTS_FOR_CODE",
    "FORMAL_VERIFICATION",
    "SYMBOLIC_EXECUTION",
    "TEST_GENERATION",
    "FUZZING",
    "PROGRAM_REPAIR",
    "STATIC_ANALYSIS_SECURITY",
    "CONSTRAINED_DECODING_AND_GUARDS",
    "CONSENSUS_AND_SELECTION",
    "BENCHMARKS_AND_EVAL_FOR_CODE_AGENTS",
]
CATEGORY_SET = set(CATEGORIES)
UNCLASSIFIED = "UNCLASSIFIED"


PROMPT_TEMPLATE = """SYSTEM / INSTRUCTION
You are a strict research-paper classifier for AI-for-Software-Engineering.

TASK
Given 10 papers (title + abstract + optional keywords), assign EACH paper to EXACTLY ONE category.

CATEGORIES (choose exactly one per paper)
AGENTS_FOR_CODE
FORMAL_VERIFICATION
SYMBOLIC_EXECUTION
TEST_GENERATION
FUZZING
PROGRAM_REPAIR
STATIC_ANALYSIS_SECURITY
CONSTRAINED_DECODING_AND_GUARDS
CONSENSUS_AND_SELECTION
BENCHMARKS_AND_EVAL_FOR_CODE_AGENTS

DEFINITIONS (brief)
- AGENTS_FOR_CODE: tool-using / multi-step agents for programming (repo exploration, SWE-bench, planning+execution, multi-agent coding).
- FORMAL_VERIFICATION: LLMs inside formal verification (contracts/invariants/assertions, SMT/provers, Dafny/Verus/Lean/Coq/Rocq).
- SYMBOLIC_EXECUTION: LLMs integrated with symbolic execution (constraints, path exploration, modeling), or SE guiding LLMs.
- TEST_GENERATION: generating tests/oracles (unit/property/regression/differential), execution-feedback loops.
- FUZZING: coverage/grammar fuzzing, LLM-guided mutators, fuzzing guidance/prioritization, fuzzing+analysis.
- PROGRAM_REPAIR: patch generation / bug fixing where deliverable is a patch, often with validators.
- STATIC_ANALYSIS_SECURITY: LLMs enhancing static analyses (taint/vuln detection, audits, path-sensitive analysis).
- CONSTRAINED_DECODING_AND_GUARDS: constraining outputs (type/grammar constraints, realizability, constrained decoding, semantic guards).
- CONSENSUS_AND_SELECTION: best-of-N, self-consistency, PRMs, voting/bootstrapping, abstention, calibration for correctness.
- BENCHMARKS_AND_EVAL_FOR_CODE_AGENTS: benchmarks/evals for code-agent reliability/security (prompt injection, tool misuse, sabotage, vuln find/patch).

OUTPUT FORMAT (STRICT)
Return ONLY valid JSON. No markdown. No extra text.

{{
  "batch_id": "{batch_id}",
  "classified": [
    {{"paper_id": "<paper_id>", "category": "<ONE_OF_THE_10_CATEGORIES>"}}
  ]
}}

RULES
- Provide exactly 10 items in "classified": one for each input paper.
- "paper_id" must exactly match one of the provided paper_id values.
- "category" must be exactly one of the 10 category strings above.

PAPERS (10 ITEMS)
{papers_block}
"""


def load_json_list(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, list):
        raise ValueError(f"Expected a JSON list in {path}, got {type(obj)}")
    return obj


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


def chunked(lst: List[Any], n: int) -> List[List[Any]]:
    return [lst[i:i+n] for i in range(0, len(lst), n)]


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


def make_papers_block(papers: List[Dict[str, Any]], abs_max_chars: int) -> str:
    lines: List[str] = []
    for i, p in enumerate(papers, start=1):
        paper_id = p.get("paper_id") or p.get("id") or p.get("forum") or f"paper_{i}"
        title = truncate(p.get("title"), 300)
        abstract = truncate(p.get("abstract"), abs_max_chars)
        keywords = normalize_keywords(p.get("keywords"))

        lines.append(f"{i}) [paper_id={paper_id}] Title: {title}")
        if keywords:
            lines.append(f"   Keywords: {keywords}")
        else:
            lines.append("   Keywords: (none)")
        if abstract:
            lines.append(f"   Abstract: {abstract}")
        else:
            # Still give it something if abstract missing
            reason = truncate(p.get("reason"), 300)
            tags = p.get("tags")
            lines.append("   Abstract: (none)")
            if reason:
                lines.append(f"   Note: {reason}")
            if tags:
                lines.append(f"   Tags: {tags}")
        lines.append("")
    return "\n".join(lines).strip()


def call_model(client: OpenAI, model: str, prompt: str) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


def load_existing_paper_ids(raw_jsonl_path: str) -> Dict[str, str]:
    """
    Resume by paper_id (safer than batch_id).
    Returns mapping paper_id -> category for already-classified entries.
    """
    mapping: Dict[str, str] = {}
    if not os.path.exists(raw_jsonl_path):
        return mapping

    with open(raw_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            parsed = try_parse_json_object(rec.get("raw_response", ""))
            if not parsed:
                continue
            classified = parsed.get("classified")
            if not isinstance(classified, list):
                continue
            for item in classified:
                pid = str(item.get("paper_id") or "").strip()
                cat = str(item.get("category") or "").strip()
                if pid and cat:
                    mapping[pid] = cat
    return mapping


def validate_classified(batch_ids: List[str], parsed: Dict[str, Any]) -> Dict[str, str]:
    """
    Ensure exactly one category per batch paper id.
    Missing/invalid -> UNCLASSIFIED.
    """
    out = {pid: UNCLASSIFIED for pid in batch_ids}

    classified = parsed.get("classified")
    if not isinstance(classified, list):
        return out

    for item in classified:
        pid = str(item.get("paper_id") or "").strip()
        cat = str(item.get("category") or "").strip()
        if pid in out and cat in CATEGORY_SET:
            out[pid] = cat

    return out


def write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def extract_and_split(
    raw_jsonl_path: str,
    original_inputs: List[str],
    out_enriched_json: str,
    out_by_category_dir: str,
    out_csv_counts: Optional[str] = None,
) -> None:
    # Load original papers (merged)
    papers: List[Dict[str, Any]] = []
    for path in original_inputs:
        papers.extend(load_json_list(path))

    # Ensure stable ids
    for idx, p in enumerate(papers):
        if not (p.get("paper_id") or p.get("id") or p.get("forum")):
            p["paper_id"] = f"paper_{idx:06d}"

    # Load mapping paper_id -> category from raw_jsonl
    mapping = load_existing_paper_ids(raw_jsonl_path)

    enriched: List[Dict[str, Any]] = []
    by_cat: Dict[str, List[Dict[str, Any]]] = {c: [] for c in CATEGORIES}
    by_cat[UNCLASSIFIED] = []

    for p in papers:
        pid = str(p.get("paper_id") or p.get("id") or p.get("forum") or "")
        cat = mapping.get(pid, UNCLASSIFIED)
        q = dict(p)
        q["category"] = cat
        enriched.append(q)

        if cat not in by_cat:
            by_cat[UNCLASSIFIED].append(q)
        else:
            by_cat[cat].append(q)

    write_json(out_enriched_json, enriched)

    os.makedirs(out_by_category_dir, exist_ok=True)
    for cat, items in by_cat.items():
        write_json(os.path.join(out_by_category_dir, f"{cat}.json"), items)

    if out_csv_counts:
        os.makedirs(os.path.dirname(out_csv_counts) or ".", exist_ok=True)
        with open(out_csv_counts, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["category", "count"])
            w.writeheader()
            for cat in CATEGORIES + [UNCLASSIFIED]:
                w.writerow({"category": cat, "count": len(by_cat.get(cat, []))})


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--inputs",
        nargs="+",
        default=[],
        help="One or more JSON files (lists of papers) to classify.",
    )
    ap.add_argument(
        "--out_raw_jsonl",
        required=True,
        help="Where to write raw batch results (JSONL).",
    )

    ap.add_argument("--model", default="deepseek-reasoner")
    ap.add_argument("--base_url", default="https://api.openai-proxy.org/v1")
    ap.add_argument("--batch_size", type=int, default=10)
    ap.add_argument("--abs_max_chars", type=int, default=2000)
    ap.add_argument("--sleep_s", type=float, default=0.0)
    ap.add_argument("--max_batches", type=int, default=0)

    # Extraction outputs (optional)
    ap.add_argument("--extract_out_enriched_json", default="")
    ap.add_argument("--extract_out_by_category_dir", default="")
    ap.add_argument("--extract_out_csv_counts", default="")

    ap.add_argument(
        "--extract_only",
        action="store_true",
        help="Do not call the model; only extract/split using existing --out_raw_jsonl.",
    )

    ap.add_argument(
        "--overwrite_raw",
        action="store_true",
        help="DANGEROUS: overwrite --out_raw_jsonl (default behavior is append/resume).",
    )

    args = ap.parse_args()

    if args.extract_only:
        if not args.extract_out_enriched_json or not args.extract_out_by_category_dir:
            raise ValueError("--extract_only requires --extract_out_enriched_json and --extract_out_by_category_dir")
        extract_and_split(
            raw_jsonl_path=args.out_raw_jsonl,
            original_inputs=args.inputs,
            out_enriched_json=args.extract_out_enriched_json,
            out_by_category_dir=args.extract_out_by_category_dir,
            out_csv_counts=args.extract_out_csv_counts or None,
        )
        print(f"Extracted -> {args.extract_out_enriched_json}")
        print(f"Split into -> {args.extract_out_by_category_dir}")
        if args.extract_out_csv_counts:
            print(f"Counts CSV -> {args.extract_out_csv_counts}")
        return

    if not args.inputs:
        raise ValueError("You must provide --inputs unless using --extract_only")

    api_key = os.environ.get("CLOSE_API_KEY")
    if not api_key:
        raise ValueError("CLOSE_API_KEY is not set in environment.")

    client = OpenAI(base_url=args.base_url, api_key=api_key)

    papers: List[Dict[str, Any]] = []
    for path in args.inputs:
        papers.extend(load_json_list(path))

    # Ensure every paper has a stable paper_id
    for idx, p in enumerate(papers):
        if not (p.get("paper_id") or p.get("id") or p.get("forum")):
            p["paper_id"] = f"paper_{idx:06d}"

    batches = chunked(papers, args.batch_size)

    os.makedirs(os.path.dirname(args.out_raw_jsonl) or ".", exist_ok=True)

    mode = "w" if args.overwrite_raw else "a"
    if args.overwrite_raw and os.path.exists(args.out_raw_jsonl):
        print(f"WARNING: overwriting existing file: {args.out_raw_jsonl}")

    already = {} if args.overwrite_raw else load_existing_paper_ids(args.out_raw_jsonl)
    already_ids = set(already.keys())
    if mode == "a" and already_ids:
        print(f"Resume: found {len(already_ids)} already-classified paper_ids in {args.out_raw_jsonl}")

    written = 0
    with open(args.out_raw_jsonl, mode, encoding="utf-8") as out:
        for bi, batch in enumerate(batches, start=1):
            if args.max_batches and bi > args.max_batches:
                break

            batch_id = f"batch_{bi:05d}"

            batch_paper_ids = [
                b.get("paper_id") or b.get("id") or b.get("forum") for b in batch
            ]

            # Skip calling the model if all papers in this batch were already classified
            if all(pid in already_ids for pid in batch_paper_ids):
                print(f"Skipping batch {batch_id} (all paper_ids already classified)")
                continue

            papers_block = make_papers_block(batch, args.abs_max_chars)
            prompt = PROMPT_TEMPLATE.format(batch_id=batch_id, papers_block=papers_block)

            raw = call_model(client, args.model, prompt)
            parsed = try_parse_json_object(raw) or {}

            # Validate per-paper categories; ensure all 10 appear
            mapping = validate_classified(batch_paper_ids, parsed)

            record = {
                "batch_id": batch_id,
                "model": args.model,
                "input_files": args.inputs,
                "paper_ids": batch_paper_ids,
                "prompt": prompt,
                "raw_response": raw,
                "classified_map": mapping,  # handy for debugging
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            written += 1

            print(f"[{batch_id}] wrote classification for {len(batch)} papers")

            if args.sleep_s > 0:
                time.sleep(args.sleep_s)

    print(f"Done. Wrote {written} new raw batch records to {args.out_raw_jsonl}")

    if args.extract_out_enriched_json and args.extract_out_by_category_dir:
        extract_and_split(
            raw_jsonl_path=args.out_raw_jsonl,
            original_inputs=args.inputs,
            out_enriched_json=args.extract_out_enriched_json,
            out_by_category_dir=args.extract_out_by_category_dir,
            out_csv_counts=args.extract_out_csv_counts or None,
        )
        print(f"Extracted -> {args.extract_out_enriched_json}")
        print(f"Split into -> {args.extract_out_by_category_dir}")
        if args.extract_out_csv_counts:
            print(f"Counts CSV -> {args.extract_out_csv_counts}")


if __name__ == "__main__":
    main()

   
# python classify_in_categories.py \
#   --inputs /home/jim/AI_papers/all_results/combined.json \
#   --out_raw_jsonl /home/jim/AI_papers/raw_classify_in_categories.jsonl \
#   --model deepseek-reasoner \
#   --base_url https://api.openai-proxy.org/v1 \
#   --batch_size 10 \
#   --sleep_s 0.2 \
#   --extract_out_enriched_json /home/jim/AI_papers/all_results/all_kept_with_category.json \
#   --extract_out_by_category_dir /home/jim/AI_papers/all_results/by_category \
#   --extract_out_csv_counts /home/jim/AI_papers/all_results/category_counts.csv