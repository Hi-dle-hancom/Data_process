import json
import os
import re
import logging
import datetime

# 기본 로거 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# 스크립트가 실행되는 디렉토리를 기준으로 파일 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def normalize_code_spacing(code_content: str) -> str:
    """
    코드 내용의 줄바꿈을 정규화합니다.
    1. 코드 시작과 끝의 공백/줄바꿈을 제거합니다.
    2. 연속된 줄바꿈(예: \n\n\n 이상)을 한 줄의 빈 줄(\n\n)로 압축합니다.
       즉, 여러 빈 줄은 하나의 빈 줄로 만듭니다.
    """
    # 1. 코드 시작과 끝의 공백/줄바꿈 제거
    normalized_code = code_content.strip()
    
    # 2. 연속된 줄바꿈(2개 이상)을 두 개의 줄바꿈(\n\n)으로 압축
    # (예: "func1()\n\n\nfunc2()" -> "func1()\n\nfunc2()")
    normalized_code = re.sub(r'\n{2,}', r'\n\n', normalized_code)
    
    return normalized_code

def process_jsonl_file(input_filepath: str, output_filepath: str):
    """
    입력 JSONL 파일에서 'content' 필드를 읽어 줄바꿈을 정규화하고
    새로운 JSONL 파일에 저장합니다.
    """
    if not os.path.exists(input_filepath):
        logger.error(f"입력 파일 '{input_filepath}'을 찾을 수 없습니다.")
        return

    processed_count = 0
    with open(input_filepath, 'r', encoding='utf-8') as infile, \
         open(output_filepath, 'w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            try:
                data = json.loads(line)
                
                # 'messages' 필드의 'content'를 찾아서 처리
                if 'messages' in data and isinstance(data['messages'], list):
                    for message in data['messages']:
                        if message.get('role') == 'assistant' and 'content' in message:
                            original_code = message['content']
                            normalized_code = normalize_code_spacing(original_code)
                            message['content'] = normalized_code
                            processed_count += 1
                            break # assistant role content는 하나만 있다고 가정하고 다음 line으로 이동
                
                # 정규화된 데이터 다시 JSONL 형식으로 저장
                outfile.write(json.dumps(data, ensure_ascii=False) + '\n')

            except json.JSONDecodeError as e:
                logger.error(f"JSONL 파일 {input_filepath}의 {line_num}번째 줄 파싱 오류: {e}")
            except Exception as e:
                logger.error(f"JSONL 파일 {input_filepath}의 {line_num}번째 줄 처리 중 알 수 없는 오류: {e}")
                
    logger.info(f"JSONL 파일 처리 완료: '{input_filepath}' -> '{output_filepath}'")
    logger.info(f"총 {processed_count}개의 코드 블록이 정규화되었습니다.")

if __name__ == "__main__":
    # --- 사용 예시 ---
    # 1. 정규화할 원본 JSONL 파일의 경로를 여기에 지정하세요.
    #    아래는 제공해주신 JSONL 형식을 기반으로 한 예시 더미 파일 생성 코드입니다.
    #    실제 사용 시에는 이 더미 파일 생성 코드를 삭제하거나 주석 처리하고,
    #    기존 JSONL 파일의 경로를 `input_jsonl_file` 변수에 직접 지정해야 합니다.
    
    # dummy_input_file = os.path.join(SCRIPT_DIR, "sample_input_with_messages.jsonl")
    # sample_jsonl_data = [
    #     {"messages": [{"role": "user", "content": "Generate the next set of top logits for a language model."}, {"role": "assistant", "content": "import time\nimport traceback\n\nimport numpy as np\n\nfrom modules import models, shared\nfrom modules.logging_colors import logger\nfrom modules.models import load_model\nfrom modules.text_generation import generate_reply\nfrom modules.utils import check_model_loaded\n\nglobal_scores = None\n\n\ndef get_next_logits(*args, **kwargs):\n# ... (생략된 코드) ...\n"}]}
    # ]
    # with open(dummy_input_file, 'w', encoding='utf-8') as f:
    #     for entry in sample_jsonl_data:
    #         f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    # ⬇️⬇️⬇️ 이곳에 실제 원본 JSONL 파일 경로를 지정하세요! ⬇️⬇️⬇️
    input_jsonl_file = os.path.join(SCRIPT_DIR, "trainberofe.jsonl") 
    # input_jsonl_file = dummy_input_file # 실제 사용 시 기존 JSONL 파일 경로로 변경 (이 줄은 삭제)

    # 2. 결과가 저장될 새로운 JSONL 파일의 경로를 지정합니다.
    #    타임스탬프를 사용하여 기존 파일 덮어쓰기 방지
    current_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_jsonl_file = os.path.join(SCRIPT_DIR, f"train.jsonl")

    logger.info(f"입력 파일: {input_jsonl_file}")
    logger.info(f"출력 파일: {output_jsonl_file}")
    
    # JSONL 파일 처리 함수 호출
    process_jsonl_file(input_jsonl_file, output_jsonl_file)

    # 예시 더미 파일 삭제 (필요 없으면 주석 처리)
    # os.remove(dummy_input_file)