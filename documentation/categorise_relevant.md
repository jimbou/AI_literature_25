# Paper Classification (Categories)

Script:

```bash
scripts/classify_papers.py
```

This assigns each paper to **exactly one** category using an LLM, with **categories and prompt policy externalized** (editable files).

---

## Inputs / Outputs

**Input:** one or more JSON files (list of papers) containing at least:

* `paper_id` (or `id` / `forum`)
* `title`
* `abstract` (recommended)
* `keywords` (optional)

**Outputs:**

* Raw LLM logs: `--out_raw_jsonl` (append/resume safe)
* Optional extracted results:

  * `--extract_out_enriched_json` (original papers + `category`)
  * `--extract_out_by_category_dir` (one JSON per category)
  * `--extract_out_csv_counts` (category counts)

---

## Model / API
SEE:
[How to get relevant papers](./get_relevant.md)

---

## Basic Usage

```bash
python3 scripts/classify_papers.py \
  --prompt_file prompts/classify_ai_se.txt \
  --categories_file prompts/categories_ai_se.json \
  --inputs all_results/combined_kept.json \
  --out_raw_jsonl logs/classify_ai_se.raw.jsonl \
  --sleep_s 0.2 \
  --extract_out_enriched_json all_results/kept_with_category.json \
  --extract_out_by_category_dir all_results/by_category \
  --extract_out_csv_counts all_results/category_counts.csv
```

---

## Resume Behavior

Default behavior is **append + resume**:

* The script skips papers already classified in `--out_raw_jsonl`.
* Safe to stop and restart.

To restart from scratch:

```bash
--overwrite_raw
```

---

## Extract-Only Mode (No LLM Calls)

Rebuild split outputs from an existing raw jsonl:

```bash
python3 scripts/classify_papers.py \
  --extract_only \
  --categories_file prompts/categories_ai_se.json \
  --inputs all_results/combined_kept.json \
  --out_raw_jsonl logs/classify_ai_se.raw.jsonl \
  --extract_out_enriched_json all_results/kept_with_category.json \
  --extract_out_by_category_dir all_results/by_category
```

---

# Writing New Categories

Categories are defined in a JSON file, e.g.:

```bash
prompts/categories_ai_se.json
```

Format:

```json
{
  "unclassified": "UNCLASSIFIED",
  "categories": [
    {"name": "AGENTS_FOR_CODE", "definition": "tool-using / multi-step agents for programming"},
    {"name": "FORMAL_VERIFICATION", "definition": "LLMs inside verification: specs, SMT, proof assistants"}
  ]
}
```

Rules:

* `categories` must be a non-empty list
* each `name` must be unique
* `definition` is optional but strongly recommended (improves accuracy)

---

# Writing a New Classification Prompt

Prompt file example:

```bash
prompts/classify_ai_se.txt
```

It must contain these placeholders:

```text
{batch_id}
{papers_block}
{categories_block}
```

`{categories_block}` is automatically generated from your `categories_file`.

Everything else (task description, strictness, definitions style, output format wording) is customizable.
