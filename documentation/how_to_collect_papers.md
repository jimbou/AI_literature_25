
# Dataset Collection Guide

We collect conference paper datasets (title, abstract, keywords, DOI when available) via:

1. **PaperCopilot (preferred when available but limited to major AI conferences)**
2. **DBLP PACMPL scraper (fallback / PL venues)**

---

## 1️⃣ PaperCopilot (Fast Path)

If the conference/year is available on PaperCopilot, download directly.

Website:
👉 [https://papercopilot.com/](https://papercopilot.com/)

GitHub repository (paper lists JSON):
👉 [https://github.com/papercopilot/paperlists](https://github.com/papercopilot/paperlists)

### Example (NeurIPS 2025)

```bash
curl -L -o neurips2025.json \
  https://raw.githubusercontent.com/papercopilot/paperlists/main/nips/nips2025.json
```

### Workflow

1. Browse the site to confirm the conference/year exists.
2. Find the corresponding JSON path in the GitHub repo.
3. Download using `curl`.
4. Run the cleaning script (recommended).

---

## Cleaning PaperCopilot Datasets

PaperCopilot JSON files often contain:

* rejected papers
* workshop / journal tracks
* multiple tracks (main, datasets, position, etc.)
* extra metadata fields

Before using the dataset, we normalize it to:

* keep **only accepted papers**
* optionally restrict to **main track**
* keep only relevant fields:

  * `id`
  * `title`
  * `abstract`
  * `keywords`
  * (optional) `track`, `status`

Use the general cleaner:

```bash
python3 scripts/clean_papercopilot_json.py \
  --in neurips2025.json \
  --out neurips2025_cleaned.json
```

### Examples

**ICLR (main track only + accepted statuses)**

```bash
python3 scripts/clean_papercopilot_json.py \
  --in iclr2025.json \
  --out iclr2025_cleaned.json \
  --require_track main \
  --accepted_statuses poster,spotlight,oral
```

**AAAI (drop journal track, no strict status filtering)**

```bash
python3 scripts/clean_papercopilot_json.py \
  --in aaai2025.json \
  --out aaai2025_cleaned.json \
  --drop_track_substrings journal \
  --accepted_statuses ""
```


## 2️⃣ DBLP PACMPL Scraper (POPL / PLDI / OOPSLA)

Use this when:

* The conference is not on PaperCopilot
* The venue is published in PACMPL (POPL, PLDI, OOPSLA)

Script location:

```bash
scripts/dblp_pacmpl_scrape.py
```

### Install dependencies

```bash
pip install requests beautifulsoup4
```

---

## General Usage

```bash
python3 scripts/dblp_pacmpl_scrape.py \
  --dblp_url <DBLP_PACMPL_PAGE> \
  --needle "<H2 heading text>" \
  --out <OUTPUT_JSON> \
  --meta_source openalex \
  --sleep_s 0.1
```

Options:

* `--dblp_url` → PACMPL volume page (e.g., pacmpl9.html, pacmpl10.html)
* `--needle` → matches the issue `<h2>` heading
* `--needle_regex` → treat needle as regex
* `--meta_source` → `openalex | crossref | both | none`
* `--sleep_s` → delay between metadata API calls

---

## Ready Examples

### POPL 2026 (PACMPL Vol 10)

```bash
python3 scripts/dblp_pacmpl_scrape.py \
  --dblp_url https://dblp.org/db/journals/pacmpl/pacmpl10.html \
  --needle "Volume 10, Number POPL" \
  --out pacmpl10_popl.json
```

---

### PLDI 2025 (PACMPL Vol 9)

```bash
python3 scripts/dblp_pacmpl_scrape.py \
  --dblp_url https://dblp.org/db/journals/pacmpl/pacmpl9.html \
  --needle "Volume 9, Number PLDI" \
  --out pacmpl9_pldi.json
```

---

### OOPSLA 2025 – Issue 1

```bash
python3 scripts/dblp_pacmpl_scrape.py \
  --dblp_url https://dblp.org/db/journals/pacmpl/pacmpl9.html \
  --needle "Volume 9, Number OOPSLA1, 2025" \
  --out pacmpl9_oopsla1.json
```

---

### OOPSLA 2025 – Issue 2

```bash
python3 scripts/dblp_pacmpl_scrape.py \
  --dblp_url https://dblp.org/db/journals/pacmpl/pacmpl9.html \
  --needle "Volume 9, Number OOPSLA2, 2025" \
  --out pacmpl9_oopsla2.json
```

---

## Output Format

Each entry:

```json
{
  "id": "10.xxxx/yyy",
  "title": "...",
  "abstract": "...",
  "keywords": ["..."],
  "doi": "10.xxxx/yyy"
}
```

