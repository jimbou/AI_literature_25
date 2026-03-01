import json
import re
import csv
import sys
from typing import Any, Dict, Optional


def try_parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None

    s = text.strip()

    # Fast path
    if s.startswith("{") and s.endswith("}"):
        try:
            return json.loads(s)
        except Exception:
            pass

    # Fallback: extract first {...}
    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if not m:
        return None

    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def extract(raw_jsonl_path: str, out_json: str, out_csv: str):
    kept_rows = []
    batches_total = 0
    parse_failures = 0

    with open(raw_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            batches_total += 1
            record = json.loads(line)

            raw = record.get("raw_response", "")
            parsed = try_parse_json_object(raw)

            if parsed is None:
                parse_failures += 1
                continue

            if not parsed.get("kept"):
                continue

            batch_id = record.get("batch_id")

            # Extract titles from prompt
            prompt = record.get("prompt", "")
            id_to_title = {}
            for m in re.finditer(r"\[paper_id=(?P<pid>[^\]]+)\]\s+Title:\s+(?P<title>.*)", prompt):
                id_to_title[m.group("pid")] = m.group("title")

            for item in parsed["kept"]:
                pid = item.get("paper_id")
                kept_rows.append({
                    "batch_id": batch_id,
                    "paper_id": pid,
                    "title": id_to_title.get(pid, ""),
                    "relevance_score": item.get("relevance_score"),
                    "reason": item.get("reason"),
                    "tags": ";".join(item.get("tags", [])),
                })

    kept_rows.sort(key=lambda r: r["relevance_score"] or 0, reverse=True)

    summary = {
        "batches_total": batches_total,
        "parse_failures": parse_failures,
        "kept_total": len(kept_rows),
        "kept": kept_rows,
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["batch_id", "paper_id", "title", "relevance_score", "reason", "tags"]
        )
        writer.writeheader()
        writer.writerows(kept_rows)

    print(f"Done.")
    print(f"Kept papers: {len(kept_rows)}")
    print(f"Parse failures: {parse_failures}")
    print(f"JSON: {out_json}")
    print(f"CSV: {out_csv}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage:")
        print("python extract_results.py <raw_jsonl> <out_json> <out_csv>")
        sys.exit(1)

    extract(sys.argv[1], sys.argv[2], sys.argv[3])