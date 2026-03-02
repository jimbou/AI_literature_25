# Compare Kept Papers (Prompt Sensitivity)

Script:

```bash
scripts/compare_kept.py
```

Compares two “kept papers” outputs (from different screening prompts / runs) and reports:

* papers **added** (newly kept)
* papers **dropped** (previously kept, now not kept)
* papers kept in both with **relevance_score changes**
* score histogram shift (old vs new)

Useful for seeing how prompt/criteria changes affect what gets selected and how it’s scored.

---

## Input Formats Supported

Each input can be either:

1. a **JSON list** of paper dicts
2. a **JSON dict** containing a list under a key like `kept` (extractor output)

If it’s a dict and the list key is not standard, pass `--list_key`.

---

## Basic Usage

```bash
python3 scripts/compare_kept.py \
  --old_json temp/extracted_results_iclr.json \
  --new_json temp/extracted_results_iclr2.json \
  --out_json logs/iclr.prompt_diff.json \
  --out_csv logs/iclr.prompt_diff.csv
```

If your input is a dict and needs an explicit list key:

```bash
python3 scripts/compare_kept.py \
  --old_json temp/extracted_results_iclr.json \
  --new_json temp/extracted_results_iclr2.json \
  --list_key kept \
  --out_json logs/iclr.prompt_diff.json \
  --out_csv logs/iclr.prompt_diff.csv
```

---

## Outputs

### `--out_json` (report)

Contains:

* `counts`: totals + number added/dropped/changed
* `score_histograms`: old vs new distributions
* `added_examples`, `dropped_examples`, `changed_examples` (may be truncated)

### `--out_csv` (optional)

Flat table containing:

* changed papers (old/new score + delta)
* added papers
* dropped papers

Easy to sort/filter in a spreadsheet.

---

## Key Options

* `--list_key <key>`: if input JSON is a dict, take the list from this key (e.g., `kept`)
* `--top_k_examples K`: how many examples to include in the JSON report sections (default: 25)
* `--include_unchanged`: also include unchanged-score examples in the JSON report
* `--out_csv`: write a CSV summary

---

## Notes

* Paper identity is matched by `paper_id` (fallbacks: `id`, `forum`; last resort: title-based key).
* Example lists in the report are **not exhaustive** unless you set a large `--top_k_examples`.
