import os
import json
import time
import argparse
from typing import Any, Dict, List, Optional
import re
import csv
from openai import OpenAI



PROMPT_TEMPLATE = """SYSTEM / INSTRUCTION
You are an expert paper screener helping a research lab shortlist papers to read.

GOAL
Given 10 papers (title + abstract + optional keywords), select ONLY the papers that are relevant to our research field.
Be STRICT: in a typical batch of 10, you should keep 0–1 papers on average (≤10% overall). Keeping 2 is already unusual; keeping 3+ is almost certainly wrong unless the whole batch is unusually aligned.

OUR FIELD (WHAT WE WORK ON)
We work on AI for Software Engineering with an emphasis on LLM-based reasoning and agents for code.
We build methods that make LLMs more reliable on tasks like:
- code generation, debugging, and program repair
- checking correctness w.r.t. natural-language requirements
- hybrid neuro-symbolic approaches (LLMs + symbolic execution / SMT / formal methods)
- structured reasoning (intermediate states, Hoare-style reasoning, invariants, execution-state annotations)
- consensus/abstention and hallucination reduction for code (e.g., verifier-guided decoding, cross-task consistency checks)
- reliability and statistical correctness of LLM workflows (e.g., independence, reproducibility, sampling semantics)
- ambiguity detection/repair in natural-language specs/prompts for programming tasks

WE WANT PAPERS THAT HAVE AT LEAST ONE OF THESE STRONG SIGNALS
A paper is relevant only if it contains a substantive technical contribution in one (or more) of:
1) LLM agents / tool-using agents for programming or program reasoning (not just generic agents; must connect to code, program analysis, debugging, or verification).
2) Formal methods + LLMs (verification, symbolic execution, constraints/SMT, contracts/specs/invariants, static analysis).
3) Reliability methods for LLM-generated code: abstention/selection/consensus, hallucination detection, semantic consistency checks, verifier-based selection, test-time reasoning that measurably improves correctness.
4) Methods that reason about program semantics via structured intermediate representations (states, traces, postconditions, invariants, CFG-aware reasoning, loop reasoning) rather than surface-level prompting.
5) Research about ambiguity in programming prompts/specifications and systematic ways to quantify/repair it, especially tied to downstream correctness.

NOT RELEVANT (EXCLUDE)
Do NOT keep papers that are primarily about:
- new model architectures, training recipes, scaling laws, optimization, or general LLM alignment without a strong programming/verification/reliability-for-code angle
- vision/audio/robotics unless the core contribution is clearly about agent reasoning methods transferable to program reasoning AND the paper explicitly validates on programming or formal reasoning tasks
- generic NLP tasks, retrieval, summarization, text-only agents, or benchmarks unless directly centered on program correctness / code reasoning / verification
- dataset-only contributions unless the dataset is specifically for program reasoning/correctness/verification and enables new analysis aligned with our themes

SCORING (1–5) FOR KEPT PAPERS
Assign a relevance_score integer:
5 = Direct hit: strongly overlaps with our exact themes (agents for code + formal/semantic reasoning or strong reliability mechanism for code correctness).
4 = Very close: clearly in our field and likely citeable / inspiring, but not exactly our method.
3 = In-scope but peripheral: relevant angle but narrower/adjacent; still worth reading.
2 = Weakly in-scope: touches code/agents/reliability but contribution is not central or is mostly applied.
1 = Barely in-scope: technically connected to our field but unlikely to influence our work much.

OUTPUT FORMAT (STRICT)
Return ONLY valid JSON, no markdown, no extra text.

- If no papers are relevant: return an empty JSON object: {{}}
- Otherwise return:
{{
  "batch_id": "{batch_id}",
  "kept": [
    {{
      "paper_id": "<paper_id>",
      "relevance_score": 1-5,
      "reason": "<max 30 words, specific about why it matches our field>",
      "tags": ["AGENTS", "TOOL_USE", "PROGRAM_REASONING", "FORMAL_METHODS", "SYMBOLIC_EXEC", "VERIFICATION", "RELIABILITY", "CONSENSUS", "ABSTENTION", "AMBIGUITY", "WORKFLOW_STATS", "OTHER"]
    }}
  ]
}}

IMPORTANT CONSTRAINTS
- Only include papers you KEEP. Do not mention dropped papers.
- Keep as few as possible (≤1 on average per batch of 10).
- Reasons must be specific (mention the mechanism/domain, not generic “it’s about agents”).
- If you keep more than 2 papers in a batch, you must be extremely confident they all match strongly.

PAPERS (10 ITEMS)
{papers_block}
"""

def load_existing_batch_ids(raw_jsonl_path: str) -> set:
    existing = set()
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
                    existing.add(bid)
            except Exception:
                # ignore malformed lines
                pass
    return existing

def load_json_list(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, list):
        raise ValueError(f"Expected a JSON list in {path}, got {type(obj)}")
    return obj


def normalize_keywords(kw: Any) -> Optional[str]:
    """
    We pass keywords as a single short string in the prompt (or omit if empty).
    """
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
    t = " ".join(text.split())  # normalize whitespace
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 3] + "..."



def try_parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    """
    Try to parse a JSON object from model output.
    - Accepts '{}' as empty.
    - If extra text exists, tries to extract the first {...} block.
    Returns dict if successful, else None.
    """
    if not text:
        return None
    s = text.strip()

    # Fast path: exact JSON object
    if s.startswith("{") and s.endswith("}"):
        try:
            return json.loads(s)
        except Exception:
            pass

    # Fallback: extract first JSON object-like substring
    # This is intentionally simple; good enough for most "extra text" cases.
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
    """
    Reads raw batch logs (jsonl) and writes a cleaned JSON summary:
      - all kept items with score/reason/tags
      - plus batch/paper metadata where available
    Optionally writes a CSV for quick inspection.
    """
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

            # {} means no relevant papers
            kept = parsed.get("kept")
            if not kept:
                continue

            batches_with_kept += 1

            # We can only enrich with titles/abstracts if we saved them.
            # Your raw log currently contains only paper_ids + prompt.
            # We'll extract titles from the prompt (good enough for readability).
            prompt = rec.get("prompt", "")

            # Build a mapping paper_id -> title from prompt lines like:
            # 1) [paper_id=XYZ] Title: ...
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

    # Sort: most relevant first
    kept_rows.sort(key=lambda r: (r.get("relevance_score") or 0, r.get("paper_id") or ""), reverse=True)

    summary = {
        "raw_jsonl": raw_jsonl_path,
        "batches_total": batches_total,
        "batches_with_kept": batches_with_kept,
        "parse_failures": parse_failures,
        "kept_total": len(kept_rows),
        "kept": kept_rows,
    }

    # Write JSON
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Optional CSV
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

def make_papers_block(papers: List[Dict[str, Any]], abs_max_chars: int) -> str:
    lines: List[str] = []
    for i, p in enumerate(papers, start=1):
        paper_id = p.get("id") or p.get("paper_id") or p.get("forum") or f"paper_{i}"
        title = truncate(p.get("title"), 300)
        abstract = truncate(p.get("abstract"), abs_max_chars)
        keywords = normalize_keywords(p.get("keywords"))

        lines.append(f"{i}) [paper_id={paper_id}] Title: {title}")
        if keywords:
            lines.append(f"   Keywords: {keywords}")
        else:
            lines.append(f"   Keywords: (none)")
        lines.append(f"   Abstract: {abstract}")
        lines.append("")  # blank line between papers
    return "\n".join(lines).strip()


def chunked(lst: List[Any], n: int) -> List[List[Any]]:
    return [lst[i:i+n] for i in range(0, len(lst), n)]


def call_model(client: OpenAI, model: str, prompt: str) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""
def main():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--inputs",
        nargs="+",
        default=[],
        help="One or more cleaned JSON files (lists of papers). Required unless --extract_only.",
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
    ap.add_argument(
        "--sleep_s",
        type=float,
        default=0.0,
        help="Optional sleep between requests to be gentle with rate limits.",
    )
    ap.add_argument(
        "--max_batches",
        type=int,
        default=0,
        help="0 means run all batches; otherwise run at most this many.",
    )

    ap.add_argument(
        "--extract_out_json",
        default="",
        help="If set, extract readable results to this JSON after screening (or in --extract_only mode).",
    )
    ap.add_argument(
        "--extract_out_csv",
        default="",
        help="Optional CSV output for extracted results.",
    )
    ap.add_argument(
        "--extract_only",
        action="store_true",
        help="Do not call the model; only extract results from --out_raw_jsonl into --extract_out_json.",
    )

    ap.add_argument(
        "--overwrite_raw",
        action="store_true",
        help="DANGEROUS: overwrite --out_raw_jsonl (default behavior is append/resume).",
    )

    args = ap.parse_args()

    # Extraction-only mode: parse an existing raw jsonl without calling the model
    if args.extract_only:
        if not args.extract_out_json:
            raise ValueError("--extract_only requires --extract_out_json")
        extract_results_from_raw_jsonl(
            raw_jsonl_path=args.out_raw_jsonl,
            out_json_path=args.extract_out_json,
            out_csv_path=args.extract_out_csv or None,
        )
        print(f"Extracted results to: {args.extract_out_json}")
        if args.extract_out_csv:
            print(f"Also wrote CSV to: {args.extract_out_csv}")
        return

    # Non-extraction mode: require inputs
    if not args.inputs:
        raise ValueError("You must provide --inputs unless using --extract_only")

    api_key = os.environ.get("CLOSE_API_KEY")
    if not api_key:
        raise ValueError("CLOSE_API_KEY is not set in environment.")

    client = OpenAI(base_url=args.base_url, api_key=api_key)

    # Load and merge
    papers: List[Dict[str, Any]] = []
    for path in args.inputs:
        papers.extend(load_json_list(path))

    # Keep only those with title+abstract
    papers = [p for p in papers if p.get("title") and p.get("abstract")]

    batches = chunked(papers, args.batch_size)

    os.makedirs(os.path.dirname(args.out_raw_jsonl) or ".", exist_ok=True)

    # SAFE DEFAULT: append/resume unless user explicitly requests overwrite
    mode = "w" if args.overwrite_raw else "a"

    if args.overwrite_raw and os.path.exists(args.out_raw_jsonl):
        print(f"WARNING: overwriting existing file: {args.out_raw_jsonl}")

    existing_batch_ids = set()
    if mode == "a":
        existing_batch_ids = load_existing_batch_ids(args.out_raw_jsonl)
        if existing_batch_ids:
            print(f"Resume: found {len(existing_batch_ids)} existing batches in {args.out_raw_jsonl}")

    written = 0
    with open(args.out_raw_jsonl, mode, encoding="utf-8") as out:
        for bi, batch in enumerate(batches, start=1):
            if args.max_batches and bi > args.max_batches:
                break

            batch_id = f"batch_{bi:05d}"

            if mode == "a" and batch_id in existing_batch_ids:
                print(f"Skipping existing batch_id: {batch_id}")
                continue

            papers_block = make_papers_block(batch, args.abs_max_chars)
            prompt = PROMPT_TEMPLATE.format(batch_id=batch_id, papers_block=papers_block)

            raw = call_model(client, args.model, prompt)

            record = {
                "batch_id": batch_id,
                "model": args.model,
                "input_files": args.inputs,
                "paper_ids": [b.get("id") or b.get("paper_id") or b.get("forum") for b in batch],
                "prompt": prompt,
                "raw_response": raw,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            written += 1

            print(f"[{batch_id}] raw_response_len={len(raw)} out={args.out_raw_jsonl}")

            if args.sleep_s > 0:
                time.sleep(args.sleep_s)

    print(f"Done. Wrote {written} new raw batch records to {args.out_raw_jsonl}")

    # Optional: extract a readable summary immediately after screening
    if args.extract_out_json:
        extract_results_from_raw_jsonl(
            raw_jsonl_path=args.out_raw_jsonl,
            out_json_path=args.extract_out_json,
            out_csv_path=args.extract_out_csv or None,
        )
        print(f"Extracted results to: {args.extract_out_json}")
        if args.extract_out_csv:
            print(f"Also wrote CSV to: {args.extract_out_csv}")
    elif args.extract_out_csv:
        print("Warning: --extract_out_csv is ignored without --extract_out_json")


if __name__ == "__main__":
    main()