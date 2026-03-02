# MSV Lab – AI + PL Conference Screening Pipeline

This repository documents the full pipeline used to identify, score, and categorize conference papers relevant to the **MSV Lab** research agenda at the intersection of:

> Programming Languages (PL), Formal Methods, and Modern AI (LLMs / Foundation Models)

The goal is to systematically filter large top-tier conference proceedings and extract the subset of papers that are technically aligned with our research themes.

---

# 1. Overview

We processed the latest editions of:

| Venue        | Submissions | Accepted | Acceptance Rate |
| ------------ | ----------- | -------- | --------------- |
| AAAI 2025    | 12,957      | 3,032    | 23.40%          |
| NeurIPS 2025 | 21,575      | 5,290    | 24.52%          |
| ICLR 2025    | 11,603      | 3,704    | 31.92%          |
| PLDI 2025    | 316         | 90       | 28.48%          |
| POPL 2026    | 371         | 91       | 24.53%          |
| OOPSLA 2025  | 581         | 179      | 30.81%          |

**Totals:**

* Total submissions: **77,403**
* Total accepted: **12,386**
* Papers kept as relevant to MSV Lab: **881**
* Relevant fraction of accepted papers: **7.11%**

This demonstrates how narrow and specialized our intersection (PL + LLMs + semantic correctness) actually is within modern AI and PL venues.

---

# 2. Research Filtering Criteria

We used two slightly different filtering prompts:

* A **PL-focused version** (POPL / PLDI / OOPSLA)
* A broader **AI-for-SE version** (AAAI / NeurIPS / ICLR)

Both enforce:

## A paper is relevant only if it satisfies BOTH:

**(A)** Substantive Programming / PL / Formal reasoning contribution
**(B)** Modern AI (LLMs / foundation models / learned components) as a core method

Merely “using LLMs” is not enough.

---

## Strong Signals (at least one required)

A paper is kept only if it clearly includes one or more:

1. LLMs for program reasoning with semantic grounding (states, traces, invariants, specs, proofs).
2. Integration of LLMs with formal tools (SMT, symbolic execution, static analysis, abstract interpretation, type systems, proof assistants).
3. Reliability mechanisms grounded in semantic correctness (verifier-guided decoding, execution checks, abstention, consensus).
4. Agentic systems where the tools are PL/formal tools (verifiers, compilers, analyzers, fuzzers).
5. Ambiguity detection/repair for programming specs affecting correctness.

---

## Explicit Exclusions

We exclude:

* Pure PL papers with no meaningful AI component.
* Pure LLM papers with no PL/formal reasoning angle.
* Generic NLP/agents not evaluated on programming + correctness.
* Dataset-only work without semantic reasoning focus.
* LLM usage limited to formatting/autocomplete/summarization.

---

# 3. Relevance Scoring

Each kept paper receives a relevance score:

| Score | Meaning                                                      |
| ----- | ------------------------------------------------------------ |
| 5     | Direct hit: LLMs + formal/semantic reasoning for correctness |
| 4     | Very close: strong PL+LLM intersection                       |
| 3     | In-scope but peripheral                                      |
| 2     | Weakly in-scope                                              |
| 1     | Barely in-scope                                              |

### Distribution

* Score 1: 78
* Score 2: 54
* Score 3: 624
* Score 4: 86
* Score 5: 39

The majority (≈71%) are relevance 3 — meaning adjacent but not directly central to our core research thrust.

---

# 4. Categorization

After relevance filtering, all papers were categorized into exactly one of the following:

| Category                            | Count |
| ----------------------------------- | ----- |
| AGENTS_FOR_CODE                     | 260   |
| CONSENSUS_AND_SELECTION             | 260   |
| BENCHMARKS_AND_EVAL_FOR_CODE_AGENTS | 108   |
| FORMAL_VERIFICATION                 | 81    |
| CONSTRAINED_DECODING_AND_GUARDS     | 80    |
| SYMBOLIC_EXECUTION                  | 33    |
| PROGRAM_REPAIR                      | 13    |
| STATIC_ANALYSIS_SECURITY            | 12    |
| TEST_GENERATION                     | 7     |
| FUZZING                             | 2     |
| UNCLASSIFIED                        | 25    |

---

## Category Definitions

* **AGENTS_FOR_CODE** – Tool-using/multi-step coding agents (SWE-bench, repo exploration, planning+execution).
* **FORMAL_VERIFICATION** – LLMs inside verification workflows (SMT, Dafny, Lean, Verus, contracts).
* **SYMBOLIC_EXECUTION** – LLM + symbolic execution integration.
* **TEST_GENERATION** – Test/oracle generation with semantic grounding.
* **FUZZING** – LLM-guided or ML-guided fuzzing.
* **PROGRAM_REPAIR** – Patch generation with validators.
* **STATIC_ANALYSIS_SECURITY** – LLM-assisted taint/vulnerability/static analysis.
* **CONSTRAINED_DECODING_AND_GUARDS** – Semantic output constraints, type guards, realizability.
* **CONSENSUS_AND_SELECTION** – Best-of-N, self-consistency, PRMs, abstention.
* **BENCHMARKS_AND_EVAL_FOR_CODE_AGENTS** – Benchmarks and adversarial evaluations.
* **UNCLASSIFIED** – Did not cleanly fit a single category.

Notably:

* Agents and consensus together account for ~59% of relevant work.
* Symbolic execution + fuzzing + testing remain underrepresented in current LLM research.

---

# 5. Data Acquisition Notes

For AAAI / NeurIPS / ICLR:

* Programmatic scraping of accepted lists.
* Title + abstract obtained via official APIs or OpenReview.

For PL venues:

* Proceedings scraped individually.
* Some venues did not provide structured databases.
* For these, titles were scraped manually and abstracts resolved via DOI queries.
* In rare cases, abstract retrieval required individual lookup.

---

# 6. Folder Structure

```
all_results/
├── combined.json
├── all_kept_with_category.json
├── raw_classify_in_categories.jsonl
├── category_counts.csv
├── by_score/
│   ├── score_1.json
│   ├── score_2.json
│   ├── score_3.json
│   ├── score_4.json
│   └── score_5.json
└── by_category/
    ├── AGENTS_FOR_CODE.json
    ├── BENCHMARKS_AND_EVAL_FOR_CODE_AGENTS.json
    ├── CONSENSUS_AND_SELECTION.json
    ├── CONSTRAINED_DECODING_AND_GUARDS.json
    ├── FORMAL_VERIFICATION.json
    ├── FUZZING.json
    ├── PROGRAM_REPAIR.json
    ├── STATIC_ANALYSIS_SECURITY.json
    ├── SYMBOLIC_EXECUTION.json
    ├── TEST_GENERATION.json
    └── UNCLASSIFIED.json
```

---

## File Descriptions

### combined.json

All relevant papers across all venues (pre-categorization).

### all_kept_with_category.json

Full enriched dataset:

* title
* abstract
* keywords
* relevance_score
* category
* source_file

### by_score/

Papers split by relevance score (1–5).

### by_category/

Papers split by semantic research category.

### raw_classify_in_categories.jsonl

Append-only raw LLM classification outputs (audit trail / reproducibility).

### category_counts.csv

Count summary per category.

---

# 7. Pipeline Summary

1. Scrape accepted papers.
2. Normalize into structured JSON.
3. Batch papers 10-by-10.
4. Apply LLM relevance filtering with strict criteria.
5. Assign relevance score (1–5).
6. Merge into combined.json.
7. Re-batch and classify into exactly one of 10 categories.
8. Produce:

   * by_score splits
   * by_category splits
   * summary statistics

All LLM calls are:

* Logged in raw JSONL.
* Resumable.
* Deterministically parsed.
* Post-validated for completeness.

---

# 8. Observations

* Only ~7% of accepted papers across top-tier venues truly lie at the PL + LLM + semantic correctness intersection.
* Most AI venues contain significant volume but relatively low density of semantic correctness research.
* PL venues contain high-density formal work, but relatively fewer LLM-integrated contributions.
* Agents and consensus-based reliability dominate current trends.
* Symbolic execution + fuzzing integration with LLMs remains relatively underexplored.

---

# 9. Intended Use

This dataset enables:

* Literature review structuring by mechanism.
* Identifying research gaps.
* Tracking trends across venues.
* Building citation clusters.
* Prioritizing reading for lab meetings.

---

# 10. Reproducibility

All filtering and categorization:

* Was done via explicit prompts documented in the repository.
* Uses append-only JSONL logs.
* Can be re-run with identical prompts.
* Is fully auditable via stored raw model responses.



---

# 11. Model Backend

All LLM-based filtering and categorization steps in this pipeline were executed using:

> **DeepSeek-Reasoner** (via OpenAI-compatible API interface)

Specifically:

* Model: `deepseek-reasoner`
* Accessed via OpenAI-compatible `chat.completions` API
* All calls were logged in append-only JSONL files for reproducibility (`raw_*.jsonl`)

DeepSeek-Reasoner was chosen due to:

* Strong structured reasoning performance
* Reliable JSON-constrained output behavior
* Cost-effectiveness for large-scale batch processing (10-by-10 classification)

All outputs are fully auditable through the stored raw model responses.

---

**Maintained by Dimitris Bouras - MSV Lab – AI + Programming Languages Research Filtering Pipeline**
