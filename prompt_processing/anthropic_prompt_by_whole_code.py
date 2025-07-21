import json
import os
import re
import time
import random
import anthropic
import logging
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime

# Set up a basic logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# 환경 변수 로드 (스크립트 전역에서 한 번만 호출)
load_dotenv(dotenv_path='mongo.env')

# 파일 경로를 스크립트와 동일한 디렉토리로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# processed_ids 저장 파일 경로 다시 활성화
PROCESSED_IDS_FILEPATH = os.path.join(SCRIPT_DIR, "processed_ids.txt")

# --- MongoDB Document Retrieval (역순 + 스킵 기능) ---
def get_docs_sequentially(mongo_uri, db_name, collection_name, batch_fetch_size=500, processed_ids: set = None):
    """
    Retrieves documents sequentially from a MongoDB collection, in reverse _id order,
    skipping documents whose IDs are in the processed_ids set.
    Uses a generator to yield documents one by one.
    """
    if processed_ids is None:
        processed_ids = set()

    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db[collection_name]

    query = {}
    if processed_ids: # processed_ids가 있다면 쿼리에 추가
        obj_ids_to_exclude = []
        for doc_id_str in processed_ids:
            if ObjectId.is_valid(doc_id_str):
                obj_ids_to_exclude.append(ObjectId(doc_id_str))
            else:
                logger.warning(f"Invalid ObjectId string found in processed_ids: {doc_id_str}. Skipping this ID for exclusion.")
        
        if obj_ids_to_exclude:
            query = {'_id': {'$nin': obj_ids_to_exclude}}
            logger.info(f"MongoDB 쿼리에서 {len(obj_ids_to_exclude)}개의 이전에 처리된 ID를 제외합니다.")
    
    total_remaining = collection.count_documents(query) # 남은 문서 수 계산
    
    if total_remaining == 0 and not processed_ids: # processed_ids가 없는데 남은 문서가 0개인 경우 (원래 문서가 없거나 모두 처리됨)
        logger.info("MongoDB 컬렉션에 처리할 문서가 없거나 이미 모든 문서가 처리되었습니다.")
        client.close()
        return
    elif total_remaining == 0 and processed_ids: # processed_ids는 있지만, 필터링 후 남은 문서가 없는 경우
         logger.info(f"모든 문서({len(processed_ids)}개)가 이미 처리된 것으로 보입니다.")
         client.close()
         return

    logger.info(f"처리할 남은 문서 수: {total_remaining}")
    
    cursor = collection.find(query, no_cursor_timeout=False).sort('_id', -1).batch_size(batch_fetch_size)
    
    for doc in cursor:
        yield doc
    client.close()


# --- Anthropic API Setup ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("Anthropic API key is missing. Please set ANTHROPIC_API_KEY in your environment or .env file.")

MODEL_NAME = "claude-3-haiku-20240307"
anthropic_client = anthropic.Client(api_key=ANTHROPIC_API_KEY)

def get_completion_from_anthropic(prompt: str, system_prompt: str = "") -> str:
    """
    Gets a completion from the Anthropic Claude model with exponential backoff for rate limiting.
    """
    max_retries = 5  # 최대 재시도 횟수
    base_delay = 1   # 초기 대기 시간 (초)

    for i in range(max_retries):
        try:
            message = anthropic_client.messages.create(
                model=MODEL_NAME,
                max_tokens=2000, 
                temperature=0.0,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            if isinstance(message.content, list):
                return "".join(getattr(block, "text", str(block)) for block in message.content)
            return str(message.content)
        except anthropic.RateLimitError as e: # Anthropic API의 RateLimitError를 명시적으로 처리
            delay = base_delay * (2 ** i) + random.uniform(0, 1) # 지수적으로 증가하는 대기 시간 + 랜덤 백오프
            logger.warning(f"Rate limit exceeded. Retrying in {delay:.2f} seconds... (Attempt {i + 1}/{max_retries})")
            time.sleep(delay)
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            return "" # 다른 오류 시 빈 문자열 반환

    logger.error(f"Failed to get completion after {max_retries} retries due to rate limit.")
    return "" # 최대 재시도 횟수 초과 시 빈 문자열 반환

# --- System Prompt for Instruction Generation by LLM ---
SYSTEM_PROMPT_FOR_INSTRUCTION_GENERATION = (
    "You are an AI model training data generator. Your task is to analyze a given **complete Python code file** (the 'output') and formulate a natural language 'user request' (the 'input'). "
    "This request should describe the overall functionality, purpose, or high-level overview of the entire code. "
    "The request can be a **question, a command, or a statement seeking information or guidance**, in a way a user might interact with an AI assistant. "
    "Focus on the main goal and a summary of what the whole script or module does, rather than specific implementation details of individual functions or classes. All generated requests must be in English. "
    "Your output must be ONLY the natural user request, without any introductory phrases, explanations, or meta-comments like 'Based on the code...', 'A suitable user request could be:', or similar."
)

# --- Code Processing Logic for JSONL Output (통째로 처리) ---

def clean_llm_response(response: str) -> str:
    """
    Cleans the LLM response by removing common meta-commentary and extracting the core request.
    This function has been refined to be more robust.
    """
    cleaned_response = response.strip()

    patterns_to_remove = [
        r"^(?:Based on the provided code(?: snippet)?,(?: a suitable)?|A suitable)? user request could be:\n\n",
        r"^(?:Here's a natural|Natural|User) request:\n\n",
        r"^(?:The given code snippet(?: also)? (?:appears to be|is) (?:a|an) Python (?:function|class|method|utility|example|snippet|code|script) (?:that|which) (?:allows|enables|performs|creates|handles|m anages|describes|presents|outputs|generates|returns|contains) .*?\.?\n\n)?(?:(?:Based on this, )?a natural user request \(input\) that describes its functionality and purpose(?: of this code)? could be:\n\n)?",
        r"^(?:This (?:Python )?code(?: snippet)? (?:defines|implements|shows|demonstrates|provides|is) (?:a|an) .*\n\n)?(?:(?:Based on this, )?a natural user request \(input\) that describes its functionality and purpose(?: of this code)? could be:\n\n)?",
        r"\"(.*?)\"\n\n(?:This request|The above request|It) (?:describes|captures) the functionality and purpose.*",
    ]

    for pattern in patterns_to_remove:
        match = re.match(pattern, cleaned_response, re.DOTALL | re.IGNORECASE)
        if match:
            if len(match.groups()) > 0 and match.lastindex is not None and match.group(match.lastindex) is not None:
                extracted_content = match.group(match.lastindex)
                if extracted_content.strip():
                    cleaned_response = extracted_content.strip()
                    break
            else:
                cleaned_response = cleaned_response[match.end():].strip()

    if cleaned_response.startswith('"') and cleaned_response.endswith('"'):
        cleaned_response = cleaned_response[1:-1]
    
    return cleaned_response.strip()


def process_whole_code_to_jsonl_entry(raw_code_content: str):
    """
    Processes the entire code content to generate a single instruction-response pair.
    Returns a list containing one entry, or an empty list if processing fails.
    """
    code_stripped = raw_code_content.strip()
    if not code_stripped:
        return []

    # Claude-3 Haiku의 입력 토큰 제한은 200k이므로, 여기서는 임시로 6만 자 이상이면 너무 길다고 판단하여 스킵
    # 실제 모델의 최대 컨텍스트 토큰 수에 맞춰 이 값을 조정하세요.
    if len(code_stripped) > 1500 * 40: # 약 60,000자 (UTF-8 기준)
        logger.warning(f"Skipping document due to extremely large content (over 60k chars). Content starts with: {code_stripped[:100]}...")
        return []

    user_prompt_to_llm = (
        f"Given the following complete Python code, "
        f"please generate a natural user request (input) in English that describes its overall functionality, purpose, and what the entire script or module does at a high level:\n\n"
        f"[CODE]\n{code_stripped}\n[/CODE]"
    )
    
    input_command_raw = get_completion_from_anthropic(
        prompt=user_prompt_to_llm,
        system_prompt=SYSTEM_PROMPT_FOR_INSTRUCTION_GENERATION
    )

    input_command = clean_llm_response(input_command_raw)

    if not input_command:
        logger.warning(f"Skipping document due to empty or unparseable instruction after cleaning. Content starts with: {code_stripped[:100]}...")
        return []
        
    return [{
        "messages": [
            {"role": "user", "content": input_command},
            {"role": "assistant", "content": code_stripped}
        ]
    }]


def save_processed_id(doc_id: str, filepath: str = PROCESSED_IDS_FILEPATH):
    """
    Saves a single processed document ID to the separate processed_ids file.
    """
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(str(doc_id) + '\n')
        f.flush() # 버퍼 비우기
        os.fsync(f.fileno()) # 디스크에 동기화
    logger.debug(f"Saved processed ID: {doc_id} to {filepath}")


def load_processed_ids(filepath: str = PROCESSED_IDS_FILEPATH) -> set:
    """
    Loads all processed document IDs from the separate file into a set.
    """
    processed_ids = set()
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                doc_id = line.strip()
                if doc_id:
                    processed_ids.add(doc_id)
        logger.info(f"Loaded {len(processed_ids)} processed IDs from '{filepath}'.")
    else:
        logger.info(f"'{filepath}' not found. Starting with no processed IDs.")
    return processed_ids


if __name__ == "__main__":
    mongo_uri = os.getenv("MONGO_URI_SAVE")
    db_name = os.getenv("MONGO_DB_SAVE")
    collection_name = os.getenv("MONGO_COLLECTION_LOAD")
    
    logger.info(f"현재 스크립트 실행 디렉토리: {os.getcwd()}")
    logger.info(f"처리된 ID 파일 경로: {PROCESSED_IDS_FILEPATH}") # 다시 활성화
    logger.info(f"Loaded MONGO_URI_LOAD: {mongo_uri}")
    logger.info(f"Loaded MONGO_DB_LOAD: {db_name}")
    logger.info(f"Loaded MONGO_COLLECTION_LOAD: {collection_name}")
    logger.info(f"Loaded ANTHROPIC_API_KEY (first 5 chars): {ANTHROPIC_API_KEY[:5] if ANTHROPIC_API_KEY else 'N/A'}")

    if not mongo_uri or not db_name or not collection_name or not ANTHROPIC_API_KEY:
        logger.error("One or more critical environment variables (MongoDB URI, DB Name, Collection Name, or Anthropic API Key) are not loaded. Please check your 'mongo.env' file.")
        exit()

    batch_save_jsonl_size = 30 # JSONL 파일에 한 번에 저장할 항목 수

    # 이번 한 번만 새로운 파일에 저장하도록, 타임스탬프 기반의 새 파일명 생성
    current_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_jsonl_filename = os.path.join(SCRIPT_DIR, f"full_code_instructions_data_run_{current_timestamp}.jsonl")
    logger.info(f"이번 실행의 JSONL 출력 파일 경로: {output_jsonl_filename}")

    # 기존 처리된 ID 목록을 로드합니다.
    current_processed_ids = load_processed_ids(PROCESSED_IDS_FILEPATH)
    
    overall_jsonl_buffer = [] # JSONL에 쓸 데이터를 임시로 저장할 버퍼
    
    # get_docs_sequentially 함수 호출 시 processed_ids 인자 다시 전달
    for doc_index, doc in enumerate(get_docs_sequentially(mongo_uri, db_name, collection_name, batch_fetch_size=100, processed_ids=current_processed_ids)):
        doc_id = str(doc.get('_id'))

        # 이 로깅은 get_docs_sequentially 내부에서 이미 처리되므로, 여기서는 불필요할 수 있습니다.
        # 하지만 안전을 위해 남겨둘 수도 있습니다.
        if doc_id in current_processed_ids:
            logger.debug(f"Document {doc_id} (index {doc_index + 1}) was already processed (bypassed by query).") 
            continue # 실제로 쿼리에서 걸러지므로 이 부분까지 오는 경우는 드뭅니다.
            
        test_code_content = doc.get('content', '')
        
        if not test_code_content or not test_code_content.strip(): # 내용이 비어있거나 공백만 있는 경우 스킵
            logger.warning(f"Document {doc_id} has no 'content' or only whitespace. Skipping and marking as processed.")
            save_processed_id(doc_id, PROCESSED_IDS_FILEPATH) # 빈 문서도 처리된 것으로 저장
            current_processed_ids.add(doc_id)
            continue
            
        logger.info(f"\n--- Processing Document {doc_id} (First 100 chars) ---")
        logger.info(test_code_content[:100] + "..." if len(test_code_content) > 100 else test_code_content)
        
        newly_processed_entries = process_whole_code_to_jsonl_entry(test_code_content)
        
        if newly_processed_entries:
            overall_jsonl_buffer.extend(newly_processed_entries)
            # LLM 호출이 성공적으로 처리된 문서 ID를 저장하는 로직 다시 활성화
            save_processed_id(doc_id, PROCESSED_IDS_FILEPATH)
            current_processed_ids.add(doc_id) # Set에도 추가하여 메모리상에서 빠르게 확인
        else:
            # LLM 처리 실패 시에도 ID를 저장하여 다음 실행 시 다시 시도하지 않도록 할지 결정
            # (이번에는 실패한 ID도 저장하는 것으로 설정)
            logger.warning(f"Document {doc_id} processing failed (empty/unparseable LLM response or too long). Marking as processed.")
            save_processed_id(doc_id, PROCESSED_IDS_FILEPATH)
            current_processed_ids.add(doc_id)


        # 전체 버퍼가 batch_save_jsonl_size에 도달하면 JSONL에 저장
        if len(overall_jsonl_buffer) >= batch_save_jsonl_size:
            with open(output_jsonl_filename, 'a', encoding='utf-8') as f:
                for entry in overall_jsonl_buffer[:batch_save_jsonl_size]:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                f.flush()
                os.fsync(f.fileno())
            logger.info(f"{batch_save_jsonl_size} documents appended to '{output_jsonl_filename}' from overall buffer.")
            overall_jsonl_buffer = overall_jsonl_buffer[batch_save_jsonl_size:]

    # 모든 문서 처리 후 전체 버퍼에 남은 데이터 JSONL에 저장
    if overall_jsonl_buffer:
        with open(output_jsonl_filename, 'a', encoding='utf-8') as f:
            for entry in overall_jsonl_buffer:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            f.flush()
            os.fsync(f.fileno())
        logger.info(f"Remaining {len(overall_jsonl_buffer)} documents appended to '{output_jsonl_filename}' from overall buffer.")
    
    logger.info("Data generation process completed.")