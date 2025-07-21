import json
from pathlib import Path
from tqdm import tqdm

def extract_import_lines(lines):
    return [i for i, line in enumerate(lines) if line.strip().startswith(("import ", "from "))]

def adjust_imports_in_prefix(sample):
    prefix_lines = sample["prefix_code"].splitlines(keepends=True)
    target_code = sample.get("target_code", "")
    suffix_code = sample.get("suffix_code", "")

    import_indices = extract_import_lines(prefix_lines)

    if len(import_indices) < 3:
        return sample  # Nothing to adjust

    # Determine how many imports to move
    num_to_move = 1 if len(import_indices) == 3 else 2

    # Get actual line indices to move
    lines_to_move = import_indices[-num_to_move:]

    # Extract the lines
    moved_lines = [prefix_lines[i] for i in lines_to_move]

    # Remove from prefix
    prefix_lines = [line for i, line in enumerate(prefix_lines) if i not in lines_to_move]

    # Update sample
    sample["prefix_code"] = "".join(prefix_lines)
    sample["target_code"] = "".join(moved_lines) + target_code  # prepend moved imports to existing target
    sample["suffix_code"] = suffix_code
    return sample

def process_jsonl(input_path, output_path):
    input_path = Path(input_path)
    output_path = Path(output_path)
    updated = []

    with input_path.open("r", encoding="utf-8") as f:
        for line in tqdm(f, desc="[*] Adjusting import statements"):
            try:
                sample = json.loads(line)
                sample = adjust_imports_in_prefix(sample)
                updated.append(sample)
            except Exception as e:
                print(f"[!] Error: {e}")

    with output_path.open("w", encoding="utf-8") as f:
        for s in updated:
            json.dump(s, f)
            f.write("\n")

    print(f"[*] Saved adjusted dataset to {output_path}")

# 사용 예시
if __name__ == "__main__":
    process_jsonl("output_fim_sentence.jsonl", "output_sentence.jsonl")
