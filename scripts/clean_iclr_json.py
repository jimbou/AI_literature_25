import json

INPUT_FILE = "/home/jim/AI_papers/ICLR/iclr2025.json"
OUTPUT_FILE = "/home/jim/AI_papers/ICLR/iclr2025_cleaned.json"

ACCEPTED_STATUSES = {"poster", "spotlight", "oral"}

def normalize_keywords(kw):
    if kw is None:
        return []
    if isinstance(kw, list):
        return [str(k).strip() for k in kw if str(k).strip()]
    if isinstance(kw, str):
        # keywords sometimes separated by ";" in your dataset
        parts = kw.replace(",", ";").split(";")
        return [p.strip() for p in parts if p.strip()]
    return []

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

small_data = []
total = len(data)

for p in data:
    status = str(p.get("status", "")).strip().lower()
    track = str(p.get("track", "")).strip().lower()

    # Filter: main track + accepted statuses
    if track != "main":
        continue

    if status not in ACCEPTED_STATUSES:
        continue

    title = p.get("title")
    abstract = p.get("abstract")

    if not title or not abstract:
        continue

    keywords = (
        p.get("keywords")
        or p.get("keyword")
        or p.get("topics")
        or p.get("primary_area")
    )

    entry = {
        "id": p.get("id") or p.get("paper_id") or p.get("forum"),
        "title": title,
        "abstract": abstract,
        "keywords": normalize_keywords(keywords)
    }

    small_data.append(entry)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(small_data, f, ensure_ascii=False, indent=2)

print(f"Total papers in file: {total}")
print(f"Accepted main-track papers kept: {len(small_data)}")
print(f"Wrote cleaned file to: {OUTPUT_FILE}")