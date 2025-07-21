import json
import os

def convert_to_fim_format_with_original_cols(input_file_path, output_file_path):
    """
    prefix_code, target_code, suffix_code 컬럼을 포함한 원본 JSONL 파일을 읽어와
    FIM 태그를 content 필드 안에 삽입한 DeepSeek Coder Instruct 모델 학습용
    JSONL 형식으로 변환합니다. 컬럼명은 변경하지 않습니다.

    Args:
        input_file_path (str): 원본 FIM 데이터가 있는 JSONL 파일 경로.
        output_file_path (str): 변환된 FIM 데이터가 저장될 JSONL 파일 경로.
    """

    # DeepSeek Coder의 FIM 토큰 (tokenizer.json에서 확인된 정확한 값 사용)
    FIM_START = "<｜fim begin｜>"
    FIM_HOLE = "<｜fim hole｜>"
    FIM_END = "<｜fim end｜>"
    EOS_TOKEN = "<|EOT|>" # End Of Turn / End Of Text 토큰

    converted_data_entries = []

    print(f"'{input_file_path}' 파일을 읽어오는 중...")
    try:
        with open(input_file_path, 'r', encoding='utf-8') as infile:
            for line_num, line in enumerate(infile):
                try:
                    original_data_record = json.loads(line)
                    
                    # 원본 컬럼명은 그대로 유지하되, 그 값들을 가져옴
                    prefix_code = original_data_record.get("prefix_code", "")
                    target_code = original_data_record.get("target_code", "")
                    suffix_code = original_data_record.get("suffix_code", "")

                    # FIM 토큰과 코드를 결합하여 assistant의 content 생성
                    # <FIM_START> <prefix_code> <FIM_HOLE> <suffix_code> <FIM_END> <target_code> <EOS_TOKEN>
                    assistant_fim_content_raw = (
                        FIM_START + prefix_code +
                        FIM_HOLE + suffix_code +
                        FIM_END + target_code +
                        EOS_TOKEN
                    )

                    # user의 content (빈칸을 표시하는 코드)
                    user_content_str = (
                    "Please complete the blank part of the following Python code:\n\n"
                    "```python\n"
                    f"{prefix_code}"
                    "# (Complete the code here)\n"
                    f"{suffix_code}"
                    "```\n\n"
                    )

# assistant's content (wrapped in markdown code block)
                    assistant_full_content_str = (
                    "Yes, I have completed the code as requested. Here is the completed code:\n\n"
                    f"```python\n{assistant_fim_content_raw}\n```"
                    )

                    # 최종 messages 형식으로 추가할 딕셔너리
                    # 팀장님의 지시대로 원본 컬럼명은 유지하고 그 값은 변경되지 않음
                    # 하지만 학습을 위한 'messages' 필드를 추가함
                    record_for_training = {
                        "messages": [
                            {"role": "user", "content": user_content_str},
                            {"role": "assistant", "content": assistant_full_content_str}
                        ]
                    }
                    
                    # 원본 데이터를 그대로 유지하면서 'messages' 필드를 추가할 수도 있습니다.
                    # 하지만 대부분의 학습 스크립트는 'messages' 필드만 기대하므로
                    # 위와 같이 'messages'만 있는 새로운 레코드를 만드는 것이 일반적입니다.
                    # 만약 원본 데이터를 그대로 유지하고 싶다면:
                    # original_data_record["messages"] = record_for_training["messages"]
                    # converted_data_entries.append(original_data_record)
                    
                    # 여기서는 'messages' 필드만 있는 새로운 레코드를 추가합니다 (가장 일반적인 학습 방식).
                    converted_data_entries.append(record_for_training)

                except json.JSONDecodeError as e:
                    print(f"경고: {input_file_path} 파일의 {line_num + 1}번째 줄에서 JSON 파싱 오류 발생: {e}. 이 줄은 건너뜝니다.")
                except KeyError as e:
                    print(f"경고: {input_file_path} 파일의 {line_num + 1}번째 줄에서 필수 키 누락: {e}. 이 줄은 건너뜝니다.")
                except Exception as e:
                    print(f"경고: {input_file_path} 파일의 {line_num + 1}번째 줄에서 알 수 없는 오류 발생: {e}. 이 줄은 건너뜁니다.")

    except FileNotFoundError:
        print(f"오류: 입력 파일 '{input_file_path}'을(를) 찾을 수 없습니다.")
        return

    print(f"총 {len(converted_data_entries)}개의 레코드를 변환했습니다.")
    print(f"변환된 데이터를 '{output_file_path}'에 저장하는 중...")

    try:
        with open(output_file_path, 'w', encoding='utf-8') as outfile:
            for entry in converted_data_entries:
                outfile.write(json.dumps(entry, ensure_ascii=False) + '\n')
        print("변환 및 저장이 완료되었습니다.")
    except IOError as e:
        print(f"오류: 출력 파일 '{output_file_path}'에 쓰는 중 오류 발생: {e}")

# --- 스크립트 실행 부분 ---
if __name__ == "__main__":
    # TODO: 여기에 실제 입력 및 출력 파일 경로를 설정하세요.
    # 예시:
    input_jsonl_file = "short_FIM_train.jsonl"  # 원본 FIM 데이터 파일명
    output_jsonl_file = "short_train.jsonl" # 변환될 학습용 파일명

    # 테스트를 위한 더미 파일 생성 (실제 파일이 없으면 사용)
    if not os.path.exists(input_jsonl_file):
        print(f"'{input_jsonl_file}' 파일이 없으므로 테스트용 더미 파일을 생성합니다.")
        dummy_data_for_test = [
            {
                "id": "code_001",
                "prefix_code": "import math\n\ndef calculate_area(radius):\n",
                "target_code": "    return math.pi * radius**2",
                "suffix_code": "\n\nprint(calculate_area(5))"
            },
            {
                "id": "code_002",
                "prefix_code": "def factorial(n):\n    if n == 0:\n        return 1\n    else:\n",
                "target_code": "        return n * factorial(n-1)",
                "suffix_code": "\n\n# Test the function\nprint(factorial(5))"
            }
        ]
        with open(input_jsonl_file, 'w', encoding='utf-8') as f:
            for item in dummy_data_for_test:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        print("더미 파일 생성이 완료되었습니다. 스크립트를 다시 실행해주세요.")
    else:
        convert_to_fim_format_with_original_cols(input_jsonl_file, output_jsonl_file)