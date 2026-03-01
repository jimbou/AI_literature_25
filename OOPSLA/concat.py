import json

INPUT_FILE_1 = "/home/jim/AI_papers/OOPSLA/pacmpl9_oopsla1.json"
INPUT_FILE_2 = "/home/jim/AI_papers/OOPSLA/pacmpl9_oopsla2.json"
OUTPUT_FILE = "/home/jim/AI_papers/OOPSLA/oopsla.json"

with open(INPUT_FILE_1, "r", encoding="utf-8") as f:
    data1 = json.load(f)

with open(INPUT_FILE_2, "r", encoding="utf-8") as f:
    data2 = json.load(f)

# Merge
combined = data1 + data2

# Optional: remove duplicates by paper id
seen = set()
deduped = []

for paper in combined:
    pid = paper.get("id")
    if pid and pid not in seen:
        seen.add(pid)
        deduped.append(paper)
    elif not pid:
        # keep entries without id
        deduped.append(paper)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(deduped, f, ensure_ascii=False, indent=2)

print(f"File1 papers: {len(data1)}")
print(f"File2 papers: {len(data2)}")
print(f"Final papers written: {len(deduped)}")
print(f"Output saved to: {OUTPUT_FILE}")