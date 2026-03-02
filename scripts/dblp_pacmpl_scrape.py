#!/usr/bin/env python3
"""
dblp_pacmpl_scrape.py

One unified scraper for DBLP PACMPL pages (e.g., POPL/PLDI/OOPSLA issues)
that extracts: title, DOI (if present), and optionally (abstract + keywords)
via OpenAlex and/or Crossref.

Examples
--------
# POPL 2026 (PACMPL vol 10, POPL)
python dblp_pacmpl_scrape.py \
  --dblp_url https://dblp.org/db/journals/pacmpl/pacmpl10.html \
  --needle "Volume 10, Number POPL" \
  --out pacmpl10_popl.json

# PLDI 2025 (PACMPL vol 9, PLDI)
python dblp_pacmpl_scrape.py \
  --dblp_url https://dblp.org/db/journals/pacmpl/pacmpl9.html \
  --needle "Volume 9, Number PLDI" \
  --out pacmpl9_pldi.json

# OOPSLA 2025 issue 1
python dblp_pacmpl_scrape.py \
  --dblp_url https://dblp.org/db/journals/pacmpl/pacmpl9.html \
  --needle "Volume 9, Number OOPSLA1, 2025" \
  --out pacmpl9_oopsla1.json

# OOPSLA 2025 issue 2
python dblp_pacmpl_scrape.py \
  --dblp_url https://dblp.org/db/journals/pacmpl/pacmpl9.html \
  --needle "Volume 9, Number OOPSLA2, 2025" \
  --out pacmpl9_oopsla2.json
"""

import argparse
import json
import re
import time
from html import unescape
from typing import Any, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup

UA = "dblp-pacmpl-scraper/1.0 (contact: you@example.com)"


def extract_doi_from_entry(li) -> str:
    # Prefer explicit "electronic edition via DOI"
    a = li.select_one('li.ee a[href*="doi.org/10."]')
    if a and a.get("href"):
        return a["href"].split("doi.org/")[-1].strip()

    # Fallback: any doi.org link
    for a in li.select('a[href*="doi.org/10."]'):
        href = a.get("href", "")
        if "doi.org/" in href:
            return href.split("doi.org/")[-1].strip()
    return ""


def clean_jats_or_html(s: str) -> str:
    if not s:
        return ""
    s = unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_crossref_abstract(jats: str) -> str:
    return clean_jats_or_html(jats or "")


def crossref_extract_abstract_and_keywords(message: dict) -> Tuple[str, List[str]]:
    abstract = clean_crossref_abstract(message.get("abstract") or "")
    subjects = message.get("subject") or []
    keywords: List[str] = []
    if isinstance(subjects, list):
        keywords = [s.strip() for s in subjects if isinstance(s, str) and s.strip()]
    return abstract, keywords


def openalex_by_doi(doi: str, timeout_s: int = 30) -> Tuple[str, List[str]]:
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout_s)
    if r.status_code != 200:
        return "", []
    data = r.json()

    abstract = ""
    inv = data.get("abstract_inverted_index")
    if isinstance(inv, dict) and inv:
        pos_to_word: Dict[int, str] = {}
        for word, positions in inv.items():
            if not isinstance(positions, list):
                continue
            for p in positions:
                if isinstance(p, int):
                    pos_to_word[p] = word
        if pos_to_word:
            abstract = " ".join(pos_to_word[i] for i in sorted(pos_to_word.keys()))
    else:
        abstract = data.get("abstract") or ""

    abstract = clean_jats_or_html(abstract)

    kw: List[str] = []
    concepts = data.get("concepts") or []
    if isinstance(concepts, list):
        for c in concepts[:8]:
            name = c.get("display_name")
            if isinstance(name, str) and name.strip():
                kw.append(name.strip())

    return abstract, kw


def crossref_by_doi(doi: str, timeout_s: int = 30) -> Tuple[str, List[str]]:
    url = f"https://api.crossref.org/works/{doi}"
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout_s)
    if r.status_code != 200:
        return "", []
    payload = r.json() or {}
    msg = payload.get("message") or {}
    if not isinstance(msg, dict):
        return "", []
    return crossref_extract_abstract_and_keywords(msg)


def fetch_meta(doi: str, prefer: str, sleep_s: float) -> Tuple[str, List[str]]:
    abstract = ""
    keywords: List[str] = []

    if prefer in ("openalex", "both"):
        a, k = openalex_by_doi(doi)
        if a:
            abstract = a
        if k:
            keywords.extend(k)
        if sleep_s > 0:
            time.sleep(sleep_s)

    if (prefer in ("crossref", "both")) and (not abstract or not keywords):
        a2, k2 = crossref_by_doi(doi)
        if not abstract and a2:
            abstract = a2
        if k2:
            keywords.extend(k2)
        if sleep_s > 0:
            time.sleep(sleep_s)

    # de-dup preserving order
    seen = set()
    uniq: List[str] = []
    for x in keywords:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return abstract, uniq


def find_issue_h2(soup: BeautifulSoup, needle: str, needle_regex: bool) -> Any:
    """
    Locate the <h2> that starts the desired section.
    - needle_regex=False: substring match
    - needle_regex=True: regex search over heading text
    """
    rx = re.compile(needle) if needle_regex else None
    for h2 in soup.find_all("h2"):
        text = h2.get_text(" ", strip=True)
        if needle_regex:
            if rx and rx.search(text):
                return h2
        else:
            if needle in text:
                return h2
    return None


def parse_dblp_section(dblp_url: str, needle: str, needle_regex: bool) -> List[Dict[str, Any]]:
    r = requests.get(dblp_url, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    h2 = find_issue_h2(soup, needle, needle_regex)
    if h2 is None:
        raise RuntimeError(f"Could not find section heading matching: {needle}")

    papers: List[Dict[str, Any]] = []

    # Iterate forward until the next <h2> (next issue)
    for el in h2.next_elements:
        if getattr(el, "name", None) == "h2":
            break
        if getattr(el, "name", None) == "li" and "entry" in (el.get("class") or []):
            title_el = el.select_one("span.title")
            if not title_el:
                continue
            title = " ".join(title_el.get_text(" ", strip=True).split())
            doi = extract_doi_from_entry(el)
            if title:
                papers.append({"title": title, "doi": doi})

    return papers


def build_json(
    dblp_url: str,
    needle: str,
    needle_regex: bool,
    out_path: str,
    meta_source: str,
    sleep_s: float,
) -> None:
    papers = parse_dblp_section(dblp_url, needle, needle_regex)
    print(f"Found {len(papers)} papers in section: {needle}")

    out: List[Dict[str, Any]] = []
    for i, p in enumerate(papers, 1):
        doi = p["doi"]
        abstract = ""
        keywords: List[str] = []

        if doi:
            abstract, keywords = fetch_meta(doi, prefer=meta_source, sleep_s=sleep_s)

        out.append(
            {
                "id": doi or f"no_doi_{i:04d}",
                "title": p["title"],
                "abstract": abstract,
                "keywords": keywords,
                "doi": doi,
                "source": {"dblp_url": dblp_url, "needle": needle},
            }
        )

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    missing_abs = sum(1 for x in out if not x["abstract"])
    missing_doi = sum(1 for x in out if not x["doi"])
    print(f"Wrote {len(out)} papers to {out_path}")
    print(f"Missing DOIs: {missing_doi}")
    print(f"Missing abstracts: {missing_abs} (depends on OpenAlex/Crossref coverage)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dblp_url", required=True, help="DBLP page URL (e.g., pacmpl9.html, pacmpl10.html)")
    ap.add_argument(
        "--needle",
        required=True,
        help='Heading selector for the issue section. Example: "Volume 10, Number POPL" '
             'or regex like "Volume 9, Number OOPSLA[12], 2025"',
    )
    ap.add_argument(
        "--needle_regex",
        action="store_true",
        help="Treat --needle as a Python regex (re.search) instead of substring match.",
    )
    ap.add_argument("--out", required=True, help="Output JSON path.")
    ap.add_argument(
        "--meta_source",
        choices=["openalex", "crossref", "both", "none"],
        default="openalex",
        help="Where to fetch abstracts/keyword-proxies by DOI.",
    )
    ap.add_argument("--sleep_s", type=float, default=0.1, help="Sleep between metadata API calls.")
    args = ap.parse_args()

    meta_source = args.meta_source
    if meta_source == "none":
        meta_source = "openalex"  # we will skip calls by checking below

    papers = parse_dblp_section(args.dblp_url, args.needle, args.needle_regex)
    print(f"Found {len(papers)} papers in section: {args.needle}")

    out: List[Dict[str, Any]] = []
    for i, p in enumerate(papers, 1):
        doi = p["doi"]
        abstract = ""
        keywords: List[str] = []
        if args.meta_source != "none" and doi:
            abstract, keywords = fetch_meta(doi, prefer=meta_source, sleep_s=args.sleep_s)

        out.append(
            {
                "id": doi or f"no_doi_{i:04d}",
                "title": p["title"],
                "abstract": abstract,
                "keywords": keywords,
                "doi": doi,
                "source": {"dblp_url": args.dblp_url, "needle": args.needle},
            }
        )
        #temporarily save after each paper in case of long runs and to track progress
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"Processed {i}/{len(papers)}: {p['title']} (DOI: {doi}, abstract len: {len(abstract)}, keywords: {keywords})")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    missing_abs = sum(1 for x in out if not x["abstract"])
    missing_doi = sum(1 for x in out if not x["doi"])
    print(f"Wrote {len(out)} papers to {args.out}")
    print(f"Missing DOIs: {missing_doi}")
    print(f"Missing abstracts: {missing_abs} (depends on OpenAlex/Crossref coverage)")


if __name__ == "__main__":
    main()