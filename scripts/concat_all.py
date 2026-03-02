import json
import glob
import os

# Folder containing your JSON files
INPUT_DIR = "/home/jim/AI_papers/all_results"
OUTPUT_FILE = "/home/jim/AI_papers/all_results/combined.json"

all_kept = []

for filepath in glob.glob(os.path.join(INPUT_DIR, "*.json")):
    filename = os.path.basename(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

        kept_items = data.get("kept", [])

        if isinstance(kept_items, list):
            for item in kept_items:
                # Make a copy so we don't mutate original structure
                item_copy = dict(item)
                item_copy["source_file"] = filename
                all_kept.append(item_copy)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_kept, f, indent=2, ensure_ascii=False)

print(f"Saved {len(all_kept)} entries to {OUTPUT_FILE}")