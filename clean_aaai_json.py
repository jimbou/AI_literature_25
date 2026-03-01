import json

INPUT_FILE = "/home/jim/AI_papers/AAAI/aaai2025.json"
OUTPUT_FILE = "/home/jim/AI_papers/AAAI/aaai2025_cleaned.json"

def normalize_keywords(kw):
    if kw is None:
        return []
    if isinstance(kw, list):
        return [str(x).strip() for x in kw if str(x).strip()]
    if isinstance(kw, str):
        parts = kw.replace(",", ";").split(";")
        return [p.strip() for p in parts if p.strip()]
    return []

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

small = []
for p in data:
    track = str(p.get("track", "")).strip().lower()
    if "journal" in track:
        continue  # remove journal track papers

    title = p.get("title")
    abstract = p.get("abstract")
    if not title or not abstract:
        continue

    small.append({
        "id": p.get("id"),
        "title": title,
        "abstract": abstract,
        "keywords": normalize_keywords(p.get("keywords")),
        "track": p.get("track"),
        "status": p.get("status"),
    })

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(small, f, ensure_ascii=False, indent=2)

print(f"Done. Wrote {len(small)} main-track entries to {OUTPUT_FILE}")