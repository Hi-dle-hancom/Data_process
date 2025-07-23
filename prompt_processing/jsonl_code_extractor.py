import json
import os
from pathlib import Path
import re

# ✅ 직접 경로 선언
input_path = "train.jsonl"  # 여기에 입력 파일 경로
output_path = "realtrain.jsonl"  # 여기에 출력 파일 경로

def extract_code_blocks(text):
    """
    Extract Python code blocks from markdown-style content.
    Preferably extracts ```python ... ``` or fallback to full text.
    """
    code_blocks = re.findall(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    return code_blocks if code_blocks else [text.strip()]

def extract_codes_from_jsonl(input_path, output_path):
    code_data = []

    with open(input_path, 'r', encoding='utf-8') as infile:
        for line in infile:
            obj = json.loads(line)
            if 'messages' in obj:
                for msg in obj['messages']:
                    if msg.get("role") == 'assistant':
                        code_blocks = extract_code_blocks(msg['content'])
                        for code in code_blocks:
                            code_data.append({"code": code})

    with open(output_path, 'w', encoding='utf-8') as outfile:
        for code_item in code_data:
            json.dump(code_item, outfile, ensure_ascii=False)
            outfile.write('\n')

    print(f"[✓] Extracted {len(code_data)} code blocks to {output_path}")

if __name__ == "__main__":
    extract_codes_from_jsonl(input_path, output_path)
