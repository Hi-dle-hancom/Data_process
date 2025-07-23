import json
import ast

def extract_larger_chunks(code_str, min_suffix_lines=3):
    lines = code_str.splitlines()
    n = len(lines)

    try:
        tree = ast.parse(code_str)
    except Exception as e:
        return [{
            "prefix_code": "",
            "target_code": code_str,
            "suffix_code": ""
        }]

    nodes = []
    for node in tree.body:
        start = getattr(node, "lineno", None)
        end = getattr(node, 'end_lineno', None)
        if start is None or end is None:
            end = start
        nodes.append((start, end))

    chunks = []
    targets = []
    for (start, end) in nodes:
        start_idx = start - 1
        end_idx = end
        target_code = "\n".join(lines[start_idx:end_idx])
        targets.append(target_code)

    for i, (start, end) in enumerate(nodes):
        start_idx = start - 1
        end_idx = end

        if i == 0:
            prefix_code = "\n".join(lines[max(0, 0):start_idx])
            if not prefix_code.strip():
                prefix_code = "\n".join(lines[max(0, start_idx - min_suffix_lines):start_idx])
        else:
            prefix_code = targets[i - 1]

        target_code = targets[i]

        if i == len(nodes) - 1:
            suffix_code = ""
        else:
            next_lines = targets[i + 1].splitlines()
            suffix_code = "\n".join(next_lines[:min_suffix_lines])

        # prefix_code나 suffix_code가 빈 문자열이거나 공백만 있을 경우 청크 버림
        if not prefix_code.strip() or not suffix_code.strip():
            continue

        chunks.append({
            "prefix_code": prefix_code,
            "target_code": target_code,
            "suffix_code": suffix_code
        })

    return chunks

def process_jsonl_with_larger_chunks(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as fin, \
         open(output_path, 'w', encoding='utf-8') as fout:
        for line in fin:
            if not line.strip():
                continue
            data = json.loads(line)
            code_str = data.get("content", "")
            if not code_str.strip():
                continue

            chunks = extract_larger_chunks(code_str)
            for chunk in chunks:
                fout.write(json.dumps(chunk, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    input_file = "data.jsonl"
    output_file = "output_filtered_chunks.jsonl"
    process_jsonl_with_larger_chunks(input_file, output_file)
