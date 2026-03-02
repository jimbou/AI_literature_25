# Paper Screening with LLM

Script:

```
scripts/screen_papers.py
```

This script:

* Reads one or more cleaned JSON datasets
* Sends papers in batches (default: 10) to an LLM
* Logs raw responses to a `.jsonl` file (resume-safe)
* Optionally extracts a clean summary JSON + CSV

---

## Model & API Setup

Default configuration:

* Model: `deepseek-reasoner`
* Provider: Close AI

The script assumes the environment variable is set:

```bash
export CLOSE_API_KEY=your_api_key_here
```

If not set, it will fail.

You can override:

```
--model <model_name>
--base_url <api_url>
```

---

## Basic Usage

```bash
python3 scripts/screen_papers.py \
  --prompt_file prompts/ai_se.txt \
  --inputs data/neurips2025_cleaned.json \
  --out_raw_jsonl logs/neurips2025.raw.jsonl \
  --extract_out_json logs/neurips2025.kept.json \
  --extract_out_csv logs/neurips2025.kept.csv
```

---

## Key Options

* `--prompt_file` → prompt policy file
* `--inputs` → one or more cleaned JSON files
* `--out_raw_jsonl` → raw batch logs
* `--extract_out_json` → readable summary JSON
* `--extract_out_csv` → optional CSV export
* `--batch_size` → default 10
* `--max_batches` → limit for testing
* `--overwrite_raw` → restart from scratch

---

## Resume Behavior

Default behavior is **append + resume**:

* Existing `batch_id`s in `--out_raw_jsonl` are skipped.
* Safe to stop and restart at any time.

To force a fresh run:

```bash
--overwrite_raw
```

---

# Writing a New Prompt Policy

Prompts live in:

```
prompts/
```

Examples:

```
ai_se.txt
pl_ai.txt
template.txt
```

---

## Prompt Requirements

Each prompt file **must contain exactly two placeholders**:

```
{batch_id}
{papers_block}
```

Do not remove or rename them.

Everything else is fully customizable.

---

## Creating a New Screening Policy

1. Copy `template.txt`
2. Rename it (e.g., `agents_strict.txt`)
3. Edit:

   * Research focus
   * Inclusion criteria
   * Exclusion criteria
   * Tag list

Run:

```bash
python3 scripts/screen_papers.py \
  --prompt_file prompts/agents_strict.txt \
  --inputs data/some_conference.json \
  --out_raw_jsonl logs/some_conf.raw.jsonl
```

---
