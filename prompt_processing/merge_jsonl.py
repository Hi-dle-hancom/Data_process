import json
import os
import sys
import datetime

def merge_jsonl_files(input_filepaths: list[str], output_filepath: str):
    """
    두 개 이상의 JSONL 파일을 읽어 하나의 새로운 JSONL 파일로 병합합니다.
    """
    merged_count = 0
    
    # 출력 파일이 이미 존재하면 경고 메시지 출력
    if os.path.exists(output_filepath):
        print(f"경고: 출력 파일 '{output_filepath}'이(가) 이미 존재합니다. 덮어쓰거나, 새로운 파일을 생성합니다.")
        # 사용자에게 덮어쓸지 새 파일로 만들지 물어볼 수도 있습니다.
        # 여기서는 기본적으로 덮어쓰는 것으로 가정합니다.

    with open(output_filepath, 'w', encoding='utf-8') as outfile:
        for input_file in input_filepaths:
            if not os.path.exists(input_file):
                print(f"오류: 입력 파일 '{input_file}'을(를) 찾을 수 없습니다. 건너뜁니다.", file=sys.stderr)
                continue
            
            print(f"파일 '{input_file}' 병합 중...")
            with open(input_file, 'r', encoding='utf-8') as infile:
                for line_num, line in enumerate(infile):
                    try:
                        # 각 라인이 유효한 JSON인지 확인 (선택 사항)
                        json_obj = json.loads(line)
                        outfile.write(json.dumps(json_obj, ensure_ascii=False) + '\n')
                        merged_count += 1
                    except json.JSONDecodeError as e:
                        print(f"경고: 파일 '{input_file}'의 {line_num + 1}번째 라인이 유효한 JSON이 아닙니다. 건너뜁니다: {e}", file=sys.stderr)
                    except Exception as e:
                        print(f"경고: 파일 '{input_file}'의 {line_num + 1}번째 라인 처리 중 예상치 못한 오류 발생: {e}", file=sys.stderr)
            
            # 각 파일 처리 후 버퍼 비우고 디스크에 동기화
            outfile.flush()
            os.fsync(outfile.fileno())

    print(f"\n병합 완료! 총 {merged_count}개의 JSON 객체가 '{output_filepath}'에 저장되었습니다.")

if __name__ == '__main__':
    # 병합할 입력 JSONL 파일 목록
    # 여기에 병합하고 싶은 JSONL 파일 경로를 추가하세요.
    # 예시: ['data_part1.jsonl', 'data_part2.jsonl']
    # 현재 스크립트와 같은 디렉토리에 있다면 파일명만 적어도 됩니다.
    input_files = [
        "full_code_instructions_data_run_20250613_132808.jsonl", # 예시 파일명 1
        "full_code_instructions_data_run_20250613_135719.jsonl", # 예시 파일명 3
        # 더 많은 파일을 추가할 수 있습니다.
    ]

    # 출력될 새로운 JSONL 파일명 (실행 시 타임스탬프가 붙습니다)
    current_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"longtrain.jsonl"

    print("JSONL 파일 병합을 시작합니다...")
    merge_jsonl_files(input_files, output_filename)