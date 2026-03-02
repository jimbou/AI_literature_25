# Split by Relevance Score

Script:

```bash
scripts/split_in_5.py
```

Splits a “kept papers” JSON file into **5 separate JSON files** based on `relevance_score` (1–5).

---

## Input

A JSON file containing a **list of papers**, e.g.:

```json
[
  {"paper_id": "...", "relevance_score": 5, ...},
  {"paper_id": "...", "relevance_score": 3, ...}
]
```

---

## Basic Usage

```bash
python3 scripts/split_in_5.py \
  --in_json all_results/combined_kept.json \
  --out_dir all_results/by_score
```

This produces:

```
by_score/
  score_1.json
  score_2.json
  score_3.json
  score_4.json
  score_5.json
```

---

## Options

* `--prefix` → change output filename prefix (default: `score_`)
* `--keep_invalid` → also write `invalid_score.json` for entries with missing/invalid `relevance_score`

Example:

```bash
python3 scripts/split_in_5.py \
  --in_json combined.json \
  --out_dir by_score \
  --keep_invalid
```

---

## Notes

* Papers are sorted by `(source_file, batch_id, paper_id)` for readability.
* Entries with missing/invalid scores are skipped unless `--keep_invalid` is set.
* Original entries are preserved unchanged.
