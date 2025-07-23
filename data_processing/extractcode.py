import json

def extract_content_and_save_jsonl(input_jsonl_path: str, output_jsonl_path: str):
    """
    input_jsonl_path의 각 JSON 객체에서 'content' 필드만 추출해서,
    output_jsonl_path에 {"content": "..."} 형식으로 한 줄씩 JSONL로 저장.
    """
    with open(input_jsonl_path, 'r', encoding='utf-8') as infile, \
         open(output_jsonl_path, 'w', encoding='utf-8') as outfile:

        for line_num, line in enumerate(infile, 1):
            try:
                obj = json.loads(line)
                if "content" in obj:
                    content = obj["content"].replace('\\/', '/')
                    out_obj = {"content": content}
                    json_line = json.dumps(out_obj, ensure_ascii=False)
                    outfile.write(json_line + "\n")
                else:
                    print(f"[Line {line_num}] 'content' 필드 없음, 스킵")
            except json.JSONDecodeError as e:
                print(f"[Line {line_num}] JSONDecodeError: {e}")
extract_content_and_save_jsonl(
    input_jsonl_path="output_data.jsonl",
    output_jsonl_path='data.jsonl'
)

