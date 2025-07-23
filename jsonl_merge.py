import json
from pathlib import Path
from tqdm import tqdm
from collections import OrderedDict

def reorder_keys(obj):
    return OrderedDict([
        ("prefix_code", obj.get("prefix_code", "")),
        ("target_code", obj.get("target_code", "")),
        ("suffix_code", obj.get("suffix_code", "")),
    ])

def merge_jsonl_unique(files, output_file):
    seen = set()
    output_path = Path(output_file)

    with output_path.open("w", encoding="utf-8") as fout:
        for filename in files:
            with open(filename, "r", encoding="utf-8") as f:
                for line in tqdm(f, desc=f"Reading {filename}"):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        obj_ordered = reorder_keys(obj)
                    except json.JSONDecodeError:
                        print(f"[!] Failed to parse JSON in file {filename}: {line[:50]}...")
                        continue
                    obj_str = json.dumps(obj_ordered, ensure_ascii=False)
                    if obj_str not in seen:
                        seen.add(obj_str)
                        fout.write(obj_str + "\n")

    print(f"[*] Merged {len(files)} files with unique samples saved to {output_file}")

if __name__ == "__main__":
    input_files = [
        "merged_unique4.jsonl",
        "merged_unique5.jsonl",
    ]
    output_file = 'merged_unique6.jsonl'
    merge_jsonl_unique(input_files, output_file)
