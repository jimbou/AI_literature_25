import argparse
import json
import re
import time
from html import unescape
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

DBLP_PACMPL9 = "https://dblp.org/db/journals/pacmpl/pacmpl9.html"

# import requests
# from typing import List, Tuple

UA = "pacmpl-oopsla-scraper/1.0 (contact: you@example.com)"

import re

def extract_doi_from_entry(li) -> str:
    # Prefer the explicit "electronic edition via DOI" link
    a = li.select_one('li.ee a[href*="doi.org/10."]')
    if a and a.get("href"):
        return a["href"].split("doi.org/")[-1].strip()

    # Fallback: first doi.org link anywhere in this entry
    for a in li.select('a[href*="doi.org/10."]'):
        href = a.get("href", "")
        if "doi.org/" in href:
            return href.split("doi.org/")[-1].strip()

    return ""

def clean_jats_or_html(s: str) -> str:
    if not s:
        return ""
    s = unescape(s)
    # remove tags (Crossref/OpenAlex sometimes include HTML/JATS-ish fragments)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s
import re
from html import unescape
from typing import List, Tuple

def clean_crossref_abstract(jats: str) -> str:
    """
    Crossref abstracts often come as JATS XML, e.g. <jats:p>...</jats:p>.
    Strip tags, unescape entities, normalize whitespace.
    """
    if not jats:
        return ""
    s = unescape(jats)
    # remove any tags (jats or otherwise)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def crossref_extract_abstract_and_keywords(message: dict) -> Tuple[str, List[str]]:
    abstract = clean_crossref_abstract(message.get("abstract") or "")
    subjects = message.get("subject") or []
    keywords: List[str] = []
    if isinstance(subjects, list):
        keywords = [s.strip() for s in subjects if isinstance(s, str) and s.strip()]
    return abstract, keywords

def openalex_by_doi(doi: str, timeout_s: int = 30) -> Tuple[str, List[str]]:
    """
    Returns (abstract, keywords_proxy).
    OpenAlex abstracts are often inverted index; we reconstruct.
    Keywords proxy: top concept names (if present).
    """
    # OpenAlex requires URL encoding of DOI:
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout_s)
    if r.status_code != 200:
        return "", []
    data = r.json()

    # Abstract: OpenAlex uses "abstract_inverted_index" often.
    abstract = ""
    inv = data.get("abstract_inverted_index")
    if isinstance(inv, dict) and inv:
        # reconstruct by position
        # inv: word -> [positions]
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
        # sometimes there's a plain abstract (rare)
        abstract = data.get("abstract") or ""

    abstract = clean_jats_or_html(abstract)

    # "keywords": OpenAlex has "concepts" (not author keywords, but decent proxy)
    kw: List[str] = []
    concepts = data.get("concepts") or []
    if isinstance(concepts, list):
        # take top few high-level concepts
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

    abstract, keywords = crossref_extract_abstract_and_keywords(msg)
    return abstract, keywords

def fetch_meta(doi: str, prefer: str, sleep_s: float) -> Tuple[str, List[str]]:
    """
    prefer: "openalex", "crossref", or "both"
    """
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

    # de-dup keywords preserving order
    seen = set()
    uniq = []
    for x in keywords:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return abstract, uniq

def parse_oopsla_section(issue: str) -> List[Dict[str, Any]]:
    """
    issue: "OOPSLA1" or "OOPSLA2"
    Returns list of items with title + doi (if present) in that issue section.
    """
    assert issue in ("OOPSLA1", "OOPSLA2")

    r = requests.get(DBLP_PACMPL9, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    needle = f"Volume 9, Number {issue}, 2025"
    h2 = None
    for cand in soup.find_all("h2"):
        if needle in cand.get_text(" ", strip=True):
            h2 = cand
            break
    if h2 is None:
        raise RuntimeError(f"Could not find section heading: {needle}")

    papers: List[Dict[str, Any]] = []

    # Iterate forward until the next <h2> (next issue)
    for el in h2.next_elements:
        if getattr(el, "name", None) == "h2":
            break

        # DBLP entries are <li class="entry ...">
        if getattr(el, "name", None) == "li" and "entry" in (el.get("class") or []):
            title_el = el.select_one("span.title")
            
            # print("----- RAW ENTRY -----")
            # print(el.prettify())   # full HTML structure
            # print("---------------------")
            # break  # stop after first one for debugging
            if not title_el:
                continue
            title = " ".join(title_el.get_text(" ", strip=True).split())

            doi = extract_doi_from_entry(el)

            if title:
                papers.append({"title": title, "doi": doi})

    return papers

def build_json(section: str, out_path: str, meta_source: str, sleep_s: float) -> None:
    assert section in ("OOPSLA1", "OOPSLA2")
    papers = parse_oopsla_section(section)
    print(f"Found {len(papers)} papers in section {section} on DBLP.")
    out: List[Dict[str, Any]] = []
    for i, p in enumerate(papers, 1):
        doi = p["doi"]
        abstract = ""
        keywords: List[str] = []

        if doi:
            abstract, keywords = fetch_meta(doi, prefer=meta_source, sleep_s=sleep_s)

        out.append(
            {
                "id": doi or f"{section.lower()}_pacmpl9_{i:04d}",
                "title": p["title"],
                "abstract": abstract,
                "keywords": keywords,  # may be empty; OpenAlex concepts are a proxy
            }
        )

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    missing_abs = sum(1 for x in out if not x["abstract"])
    print(f"Wrote {len(out)} papers to {out_path}")
    print(f"Missing abstracts: {missing_abs} (depends on OpenAlex/Crossref coverage)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", choices=["oopsla1", "oopsla2", "both"], default="both")
    ap.add_argument("--out_dir", default=".")
    ap.add_argument("--meta_source", choices=["openalex", "crossref", "both"], default="openalex",
                    help="Where to fetch abstracts/keyword-proxies by DOI.")
    ap.add_argument("--sleep_s", type=float, default=0.1,
                    help="Sleep between metadata API calls to be polite.")
    args = ap.parse_args()

    if args.section in ("oopsla1", "both"):
        build_json("OOPSLA1", f"{args.out_dir}/pacmpl9_oopsla1.json", args.meta_source, args.sleep_s)
    if args.section in ("oopsla2", "both"):
        build_json("OOPSLA2", f"{args.out_dir}/pacmpl9_oopsla2.json", args.meta_source, args.sleep_s)


if __name__ == "__main__":
    main()