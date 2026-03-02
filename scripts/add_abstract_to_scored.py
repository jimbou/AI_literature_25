import json

JSON1_PATH = "/home/jim/AI_papers/all_results/by_score/score_5.json"   # contains the selected papers
JSON2_PATH = "/home/jim/AI_papers/all_results/combined.json"   # contains full metadata
OUTPUT_PATH = "/home/jim/AI_papers/all_results/by_score/score_5_expanded.json"

# Load files
with open(JSON1_PATH, "r", encoding="utf-8") as f:
    data1 = json.load(f)

with open(JSON2_PATH, "r", encoding="utf-8") as f:
    data2 = json.load(f)

# Build lookup dictionary from JSON2 (paper_id -> full entry)
lookup = {p["paper_id"]: p for p in data2}

merged = []

for p1 in data1:
    pid = p1["paper_id"]

    if pid in lookup:
        full_entry = lookup[pid].copy()

        # Optional: override fields from JSON1 if you want
        # (e.g., keep relevance_score from JSON1)
        full_entry.update({
            "relevance_score": p1.get("relevance_score"),
            "reason": p1.get("reason"),
            "tags": p1.get("tags"),
            "source_file_screening": p1.get("source_file")
        })

        merged.append(full_entry)
    else:
        print(f"Warning: paper_id {pid} not found in JSON2")

# Save result
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)

print(f"Saved {len(merged)} merged papers to {OUTPUT_PATH}")