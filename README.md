
# MSV Lab – AI + PL Literature Screening Pipeline

This repository contains an automated pipeline for identifying and organizing conference papers aligned with the **MSV Lab** research focus:

> Programming Languages + Formal Methods + Modern AI (LLMs)

The goal is to systematically reduce large conference proceedings to the small subset relevant to semantic program reasoning and AI-driven correctness.

---

# Pipeline Overview

The workflow consists of five stages:

1. **Collect conference papers**
2. **Clean and normalize datasets**
3. **Screen for relevance (LLM-based)**
4. **Categorize relevant papers**
5. **Analyze prompt sensitivity / score splits**

Each stage has its own guide.

---

# Step-by-Step Guides

## 1️⃣ Collect Papers

See:

[How to Collect Papers](./documentation/how_to_collect_papers.md)


Covers:

* PaperCopilot downloads
* PACMPL (POPL / PLDI / OOPSLA) scraping
* Cleaning datasets before screening

---

## 2️⃣ Screen for Relevance

See:


[Screen for Relevant Papers](./documentation/get_relevant.md)

Covers:

* LLM-based filtering
* Prompt customization
* Resume-safe execution
* Extracting kept papers

---

## 3️⃣ Categorize Relevant Papers

See:

[Categorise Relevant Papers](./documentation/categorise_relevant.md)

Covers:

* Category definitions (external JSON)
* Custom classification prompts
* Splitting outputs by category
* Extract-only mode

---

## 4️⃣ Compare Prompt Variants

See:

[Compare Prompt Differences](./documentation/compare_diffs.md)

Covers:

* Comparing two screening runs
* Detecting added / dropped papers
* Measuring score shifts
* Histogram changes

---

## 5️⃣ Split by Relevance Score

See:

[Split by Relevance Score](./documentation/split_in_5_categories.md)

Covers:

* Splitting kept papers into score_1–score_5
* Handling invalid scores

---

# Research Scope (High-Level)

A paper is considered relevant only if it:

* Involves substantive programming / PL / formal reasoning about code
  **AND**
* Uses modern AI (LLMs / learned components) as a core technical mechanism

Exact filtering logic is defined in prompt files under:

```
prompts/
```

---

# Model Backend

Default configuration:

* Model: `deepseek-reasoner`
* Requires environment variable:

```bash
export CLOSE_API_KEY=your_api_key_here
```

All LLM calls are logged (`.jsonl`) for reproducibility and auditing.

---

# Recommended Repository Layout

```
prompts/
scripts/
data/
logs/
all_results/
```

---

# Processed Conferences (2025–2026)

| Venue        | Submissions | Accepted | Acceptance |
| ------------ | ----------: | -------: | ---------: |
| AAAI 2025    |      12,957 |    3,032 |      23.4% |
| NeurIPS 2025 |      21,575 |    5,290 |      24.5% |
| ICLR 2025    |      11,603 |    3,704 |      31.9% |
| PLDI 2025    |         316 |       90 |      28.5% |
| POPL 2026    |         371 |       91 |      24.5% |
| OOPSLA 2025  |         581 |      179 |      30.8% |

**Totals**

* Submissions: **77,403**
* Accepted: **12,386**
* Papers kept as relevant: **879**
* Relevant fraction of accepted: **7.1%**

This reflects how narrow the intersection (PL + LLMs + semantic correctness) is within top-tier venues.

---

# Understanding `all_results/`

All final outputs are stored in:

```
all_results/
```

**Core files**

* `combined.json` → all relevant papers (merged)
* `all_kept_with_category.json` → full enriched dataset (score + category)
* `category_counts.csv` → category distribution summary
* `raw_classify_in_categories.jsonl` → full LLM audit log

**Subdirectories**

* `by_score/` → split by relevance score (1–5)
* `by_category/` → split by research mechanism

For most analyses, use:

* `all_kept_with_category.json` (complete dataset)
* `by_score/score_5.json` (highest alignment)
* `by_category/` (mechanism-specific review)

---


This repository is a **scalable literature discovery tool**, not a perfect classifier.
Prompts and categories are fully configurable in the /prompts subdir.

Maintained by Dimitris Bouras – MSV Lab
