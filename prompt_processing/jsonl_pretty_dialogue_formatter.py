import json
from pathlib import Path

def display_and_save_dialogues_prettily(input_jsonl_path, output_prettified_path):
    """
    JSONL 파일에서 대화를 읽어 user와 assistant 턴을 구분하여 보기 좋게 출력하고 새 파일에 저장합니다.
    이때, dialogue_id는 출력하지 않습니다.
    """
    processed_count = 0
    try:
        # 출력 파일을 쓰기 모드로 엽니다. 파일이 이미 존재하면 덮어씁니다.
        with open(output_prettified_path, "w", encoding='utf-8') as outfile:
            with open(input_jsonl_path, 'r', encoding='utf-8') as infile:
                for line_num, line in enumerate(infile):
                    try:
                        dialogue_data = json.loads(line)
                        # dialogue_id를 가져오지 않거나 사용하지 않습니다.
                        messages = dialogue_data.get("messages", [])

                        # 콘솔 출력 및 파일 저장 시 dialogue_id 제거
                        # 각 대화 시작을 알리는 구분자만 출력합니다.
                        output_line = f"--- Dialogue {processed_count+1} ---\n" # 순번으로 대체
                        print(output_line, end='')
                        outfile.write(output_line)

                        for message in messages:
                            role = message.get("role", "unknown_role")
                            content = message.get("content", "")

                            if role == "user":
                                formatted_content = f"User:\n{content}\n\n"
                            elif role == "assistant":
                                formatted_content = f"Assistant:\n{content}\n\n"
                            else:
                                formatted_content = f"{role.capitalize()}:\n{content}\n\n"
                            
                            print(formatted_content, end='') # 콘솔 출력
                            outfile.write(formatted_content)  # 파일 저장

                        separator = "-" * 30 + "\n\n" # 각 대화 끝에 구분선 추가 (두 줄 띄움)
                        print(separator, end='')
                        outfile.write(separator)
                        processed_count += 1

                    except json.JSONDecodeError as e:
                        error_msg = f"오류: '{input_jsonl_path}' 파일의 {line_num+1}번째 줄 파싱 중 오류 발생: {e}\n"
                        print(error_msg, end='')
                        outfile.write(error_msg)
                    except Exception as e:
                        error_msg = f"오류: '{input_jsonl_path}' 파일의 {line_num+1}번째 줄 처리 중 알 수 없는 오류 발생: {e}\n"
                        print(error_msg, end='')
                        outfile.write(error_msg)

        print(f"\n[*] 총 {processed_count}개의 대화가 성공적으로 처리되어 '{output_prettified_path}'에 저장되었습니다.")

    except FileNotFoundError:
        print(f"오류: '{input_jsonl_path}' 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"파일을 읽거나 쓰는 중 오류 발생: {e}")

if __name__ == "__main__":
    # --- 여기에 실제 파일 경로를 입력하세요 ---
    # 예시:
    # input_jsonl_file = "C:/Users/YourUser/Desktop/my_data/original_dialogues.jsonl"
    # output_prettified_file = "C:/Users/YourUser/Desktop/my_data/prettified_dialogues.txt"
    
    # 현재 스크립트와 같은 디렉토리에 있는 파일이라면 파일 이름만으로 충분합니다.
    input_jsonl_file = "moretrain.jsonl"  # 읽어올 원본 JSONL 파일
    output_prettified_file = "prettified_dialogues.txt" # 보기 좋게 저장될 새로운 텍스트 파일

    display_and_save_dialogues_prettily(input_jsonl_file, output_prettified_file)