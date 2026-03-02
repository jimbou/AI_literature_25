#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


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
    return [lst[i:i + n] for i in range(0, len(lst), n)]


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
    try:
        return json.loads(m.group(0).strip())
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
        lines.append(f"   Keywords: {keywords if keywords else '(none)'}")
        lines.append(f"   Abstract: {abstract if abstract else '(none)'}")
        lines.append("")
    return "\n".join(lines).strip()


def call_model(client: OpenAI, model: str, prompt: str) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


def load_categories(categories_file: str) -> Tuple[str, List[Dict[str, str]]]:
    data = json.load(open(categories_file, "r", encoding="utf-8"))
    unclassified = str(data.get("unclassified") or "UNCLASSIFIED").strip()

    cats = data.get("categories")
    if not isinstance(cats, list) or not cats:
        raise ValueError("categories.json must contain a non-empty 'categories' list")

    out: List[Dict[str, str]] = []
    seen = set()
    for c in cats:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name") or "").strip()
        definition = str(c.get("definition") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append({"name": name, "definition": definition})

    if not out:
        raise ValueError("No valid categories found in categories.json")

    return unclassified, out


def build_categories_block(cats: List[Dict[str, str]]) -> str:
    # Simple readable list; you can change formatting freely.
    lines = []
    for c in cats:
        if c["definition"]:
            lines.append(f"- {c['name']}: {c['definition']}")
        else:
            lines.append(f"- {c['name']}")
    return "\n".join(lines)


def load_existing_paper_ids(raw_jsonl_path: str) -> Dict[str, str]:
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


def validate_classified(batch_ids: List[str], parsed: Dict[str, Any], category_set: set, unclassified: str) -> Dict[str, str]:
    out = {pid: unclassified for pid in batch_ids}
    classified = parsed.get("classified")
    if not isinstance(classified, list):
        return out
    for item in classified:
        pid = str(item.get("paper_id") or "").strip()
        cat = str(item.get("category") or "").strip()
        if pid in out and cat in category_set:
            out[pid] = cat
    return out


def write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def extract_and_split(raw_jsonl_path: str, original_inputs: List[str], out_enriched_json: str, out_by_category_dir: str,
                      categories: List[str], unclassified: str, out_csv_counts: Optional[str] = None) -> None:
    papers: List[Dict[str, Any]] = []
    for path in original_inputs:
        papers.extend(load_json_list(path))

    for idx, p in enumerate(papers):
        if not (p.get("paper_id") or p.get("id") or p.get("forum")):
            p["paper_id"] = f"paper_{idx:06d}"

    mapping = load_existing_paper_ids(raw_jsonl_path)

    by_cat: Dict[str, List[Dict[str, Any]]] = {c: [] for c in categories}
    by_cat[unclassified] = []
    enriched: List[Dict[str, Any]] = []

    for p in papers:
        pid = str(p.get("paper_id") or p.get("id") or p.get("forum") or "").strip()
        cat = mapping.get(pid, unclassified)
        q = dict(p)
        q["category"] = cat
        enriched.append(q)
        if cat in by_cat:
            by_cat[cat].append(q)
        else:
            by_cat[unclassified].append(q)

    write_json(out_enriched_json, enriched)

    os.makedirs(out_by_category_dir, exist_ok=True)
    for cat, items in by_cat.items():
        write_json(os.path.join(out_by_category_dir, f"{cat}.json"), items)

    if out_csv_counts:
        os.makedirs(os.path.dirname(out_csv_counts) or ".", exist_ok=True)
        with open(out_csv_counts, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["category", "count"])
            w.writeheader()
            for cat in categories + [unclassified]:
                w.writerow({"category": cat, "count": len(by_cat.get(cat, []))})


def main() -> None:
    ap = argparse.ArgumentParser()

    ap.add_argument("--prompt_file", required=False, default="")
    ap.add_argument("--categories_file", required=False, default="")
    ap.add_argument("--inputs", nargs="+", default=[])
    ap.add_argument("--out_raw_jsonl", required=True)

    ap.add_argument("--model", default="deepseek-reasoner")
    ap.add_argument("--base_url", default="https://api.openai-proxy.org/v1")
    ap.add_argument("--batch_size", type=int, default=10)
    ap.add_argument("--abs_max_chars", type=int, default=2000)
    ap.add_argument("--sleep_s", type=float, default=0.0)
    ap.add_argument("--max_batches", type=int, default=0)

    ap.add_argument("--extract_out_enriched_json", default="")
    ap.add_argument("--extract_out_by_category_dir", default="")
    ap.add_argument("--extract_out_csv_counts", default="")
    ap.add_argument("--extract_only", action="store_true")
    ap.add_argument("--overwrite_raw", action="store_true")

    args = ap.parse_args()

    if args.extract_only:
        if not args.categories_file:
            raise ValueError("--extract_only requires --categories_file")
        if not args.extract_out_enriched_json or not args.extract_out_by_category_dir:
            raise ValueError("--extract_only requires --extract_out_enriched_json and --extract_out_by_category_dir")
        unclassified, cat_objs = load_categories(args.categories_file)
        categories = [c["name"] for c in cat_objs]
        extract_and_split(
            raw_jsonl_path=args.out_raw_jsonl,
            original_inputs=args.inputs,
            out_enriched_json=args.extract_out_enriched_json,
            out_by_category_dir=args.extract_out_by_category_dir,
            categories=categories,
            unclassified=unclassified,
            out_csv_counts=args.extract_out_csv_counts or None,
        )
        return

    if not args.inputs:
        raise ValueError("You must provide --inputs unless using --extract_only")
    if not args.prompt_file or not args.categories_file:
        raise ValueError("--prompt_file and --categories_file are required (unless --extract_only)")

    api_key = os.environ.get("CLOSE_API_KEY")
    if not api_key:
        raise ValueError("CLOSE_API_KEY is not set in environment.")

    prompt_template = read_text(args.prompt_file)
    for ph in ("{batch_id}", "{papers_block}", "{categories_block}"):
        if ph not in prompt_template:
            raise ValueError(f"Prompt must contain placeholder: {ph}")

    unclassified, cat_objs = load_categories(args.categories_file)
    categories = [c["name"] for c in cat_objs]
    category_set = set(categories)
    categories_block = build_categories_block(cat_objs)

    client = OpenAI(base_url=args.base_url, api_key=api_key)

    papers: List[Dict[str, Any]] = []
    for path in args.inputs:
        papers.extend(load_json_list(path))

    for idx, p in enumerate(papers):
        if not (p.get("paper_id") or p.get("id") or p.get("forum")):
            p["paper_id"] = f"paper_{idx:06d}"

    batches = chunked(papers, args.batch_size)
    os.makedirs(os.path.dirname(args.out_raw_jsonl) or ".", exist_ok=True)

    mode = "w" if args.overwrite_raw else "a"
    already = {} if args.overwrite_raw else load_existing_paper_ids(args.out_raw_jsonl)
    already_ids = set(already.keys())

    written = 0
    with open(args.out_raw_jsonl, mode, encoding="utf-8") as out:
        for bi, batch in enumerate(batches, start=1):
            if args.max_batches and bi > args.max_batches:
                break

            batch_id = f"batch_{bi:05d}"
            batch_paper_ids = [b.get("paper_id") or b.get("id") or b.get("forum") for b in batch]

            if all(pid in already_ids for pid in batch_paper_ids):
                continue

            papers_block = make_papers_block(batch, args.abs_max_chars)

            prompt = (
                prompt_template
                .replace("{batch_id}", batch_id)
                .replace("{papers_block}", papers_block)
                .replace("{categories_block}", categories_block)
            )

            raw = call_model(client, args.model, prompt)
            parsed = try_parse_json_object(raw) or {}
            mapping = validate_classified(batch_paper_ids, parsed, category_set, unclassified)

            record = {
                "batch_id": batch_id,
                "model": args.model,
                "prompt_file": args.prompt_file,
                "categories_file": args.categories_file,
                "paper_ids": batch_paper_ids,
                "raw_response": raw,
                "classified_map": mapping,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            written += 1

            print(f"[{batch_id}] out of {len(batches)} batches, wrote record for {len(batch)} papers (total written: {written})")

            if args.sleep_s > 0:
                time.sleep(args.sleep_s)

    print(f"Done. Wrote {written} new batch records to {args.out_raw_jsonl}")

    if args.extract_out_enriched_json and args.extract_out_by_category_dir:
        extract_and_split(
            raw_jsonl_path=args.out_raw_jsonl,
            original_inputs=args.inputs,
            out_enriched_json=args.extract_out_enriched_json,
            out_by_category_dir=args.extract_out_by_category_dir,
            categories=categories,
            unclassified=unclassified,
            out_csv_counts=args.extract_out_csv_counts or None,
        )


if __name__ == "__main__":
    main()