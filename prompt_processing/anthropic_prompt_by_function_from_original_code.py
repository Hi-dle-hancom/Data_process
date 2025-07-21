from pymongo import MongoClient
import time
import random
import os
from dotenv import load_dotenv
import json
import re
import anthropic
import ast
import logging
from bson.objectid import ObjectId
import datetime # datetime 모듈 임포트

# Set up a basic logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# 환경 변수 로드 (스크립트 전역에서 한 번만 호출)
load_dotenv(dotenv_path='mongo.env')

# 파일 경로를 스크립트와 동일한 디렉토리로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 기존 파일명
DEFAULT_OUTPUT_JSONL_FILEPATH = os.path.join(SCRIPT_DIR, "instructions_data.jsonl")

# processed_ids는 계속 누적하여 사용
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
    if processed_ids:
        obj_ids_to_exclude = []
        for doc_id_str in processed_ids:
            if ObjectId.is_valid(doc_id_str):
                obj_ids_to_exclude.append(ObjectId(doc_id_str))
            else:
                logger.warning(f"Invalid ObjectId string found in processed_ids: {doc_id_str}. Skipping this ID for exclusion.")
        
        if obj_ids_to_exclude:
            query = {'_id': {'$nin': obj_ids_to_exclude}}
            logger.info(f"MongoDB 쿼리에서 {len(obj_ids_to_exclude)}개의 이전에 처리된 ID를 제외합니다.")
    
    total_remaining = collection.count_documents(query)
    if total_remaining == 0:
        logger.info("모든 문서가 이미 처리되었거나, 처리할 문서가 남아있지 않습니다.")
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
                max_tokens=1500,
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
    "You are an AI model training data generator. Your task is to analyze a given Python code snippet (the 'output') and formulate a natural language 'user request' (the 'input'). "
    "This request should describe the functionality or purpose of the code, in a way a user might ask for a solution, either as a question or an imperative statement/command. "
    "Focus on the desired outcome rather than specific implementation details or meta-comments about the prompt itself. All generated requests must be in English. "
    "Your output must be ONLY the natural user request, without any introductory phrases, explanations, or meta-comments like 'Based on the code...', 'A suitable user request could be:', or similar."
)

# --- Code Processing Logic for JSONL Output ---

def get_node_source(node: ast.AST, source_lines: list[str]) -> str:
    """
    Extracts the source code for a given AST node, including decorators, docstrings, etc.
    This function should only be called with nodes that have lineno and end_lineno attributes.
    """
    if not hasattr(node, 'lineno') or not hasattr(node, 'end_lineno'):
        return ""

    start_line = node.lineno - 1
    end_line = node.end_lineno
    
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        for decorator in node.decorator_list:
            if hasattr(decorator, 'lineno') and decorator.lineno - 1 < start_line:
                start_line = decorator.lineno - 1

    extracted_lines = source_lines[start_line:end_line]
                
    if extracted_lines:
        min_indent = float('inf')
        for line in extracted_lines:
            if line.strip(): 
                indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, indent)
        
        if min_indent == float('inf'):
            return ""

        return "\n".join(line[min_indent:] for line in extracted_lines)
    return ""


def split_code_into_chunks(code_string: str) -> list[str]:
    """
    Splits the given Python code into meaningful, top-level functional units (classes, functions, or initial block)
    using the AST module. This provides more robust parsing than regex alone.
    Additionally, it now splits methods within classes into separate chunks.
    """
    code_string = code_string.strip()
    if not code_string:
        return []

    chunks = []
    source_lines = code_string.splitlines()

    try:
        tree = ast.parse(code_string)
    except SyntaxError as e:
        logger.warning(f"Skipping file due to SyntaxError in AST parsing: {e}")
        return []

    last_processed_lineno = 0

    if tree.body:
        nodes_with_lineno = [node for node in tree.body if hasattr(node, 'lineno')]
        first_executable_node_lineno = min(node.lineno for node in nodes_with_lineno) if nodes_with_lineno else None

        if first_executable_node_lineno is not None and first_executable_node_lineno > 1:
            initial_block = "\n".join(source_lines[0 : first_executable_node_lineno - 1]).strip()
            if initial_block:
                chunks.append(initial_block)
            last_processed_lineno = first_executable_node_lineno - 1

    for node in tree.body:
        if isinstance(node, ast.FunctionDef): 
            if hasattr(node, 'lineno') and node.lineno - 1 >= last_processed_lineno:
                chunk_code = get_node_source(node, source_lines)
                if chunk_code:
                    chunks.append(chunk_code)
                if hasattr(node, 'end_lineno'):
                    last_processed_lineno = node.end_lineno
        
        elif isinstance(node, ast.ClassDef): 
            class_start_line = node.lineno - 1
            class_end_line = node.end_lineno

            class_header_end_lineno = class_start_line
            if node.body:
                first_class_body_node = next((n for n in node.body if hasattr(n, 'lineno')), None)
                if first_class_body_node:
                    class_header_end_lineno = first_class_body_node.lineno -1 
                
            class_header_code = "\n".join(source_lines[class_start_line : class_header_end_lineno]).strip()
            if class_header_code and class_header_end_lineno >= last_processed_lineno:
                chunks.append(class_header_code)
                last_processed_lineno = class_header_end_lineno

            for method_node in node.body:
                if isinstance(method_node, ast.FunctionDef): 
                    if hasattr(method_node, 'lineno') and hasattr(method_node, 'end_lineno'):
                        if method_node.lineno - 1 >= last_processed_lineno and method_node.lineno -1 >= class_header_end_lineno:
                            method_code = get_node_source(method_node, source_lines)
                            if method_code:
                                chunks.append(method_code)
                            last_processed_lineno = method_node.end_lineno
            
            if hasattr(node, 'end_lineno') and last_processed_lineno < node.end_lineno:
                remaining_class_code = "\n".join(source_lines[last_processed_lineno : node.end_lineno]).strip()
                if remaining_class_code:
                    chunks.append(remaining_class_code)
                    last_processed_lineno = node.end_lineno
            else:
                if hasattr(node, 'end_lineno'):
                    last_processed_lineno = max(last_processed_lineno, node.end_lineno)

    if last_processed_lineno < len(source_lines):
        trailing_code = "\n".join(source_lines[last_processed_lineno:]).strip()
        if trailing_code:
            if len(trailing_code.splitlines()) == 1 and len(trailing_code) < 30 and not trailing_code.startswith(('if ', 'for ', 'while ', 'try ', 'with ', 'async ')):
                pass
            else:
                chunks.append(trailing_code)
            
    filtered_chunks = []
    for chunk in chunks:
        stripped_chunk = chunk.strip()
        if not stripped_chunk:
            continue
        
        if stripped_chunk.startswith(('#!', '# -*- coding')) or (
            (stripped_chunk.count('"""') < 2 and stripped_chunk.count("'''") < 2) and 
            len(stripped_chunk.splitlines()) < 3 and 
            not stripped_chunk.strip().lower().startswith(('from ', 'import ', 'def ', 'class ', '@', 'async def'))
        ):
            continue
        
        if stripped_chunk in ('"""', "'''"):
            continue

        filtered_chunks.append(stripped_chunk)
            
    if not filtered_chunks and code_string:
        return [code_string.strip()]

    return filtered_chunks


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


def process_code_to_jsonl_entries(raw_code_content: str):
    """
    Splits the code, matches it with English command text (generated by LLM), and returns a list of entries.
    Each entry follows the {"messages": [{"role": "user", "content": "instruction"}, {"role": "assistant", "content": "code"}]} format.
    """
    code_chunks = split_code_into_chunks(raw_code_content)
    
    processed_entries = []
    
    for i, chunk in enumerate(code_chunks):
        chunk_stripped = chunk.strip()
        if not chunk_stripped:
            continue
            
        if len(chunk_stripped) > 500 and ("Copyright" in chunk_stripped or "License" in chunk_stripped):
             logger.info(f"Skipping potentially irrelevant large comment chunk {i+1} from current document.")
             continue

        user_prompt_to_llm = (
            f"Given the following Python code snippet as output, "
            f"please generate a natural user request (input) in English that describes its functionality and purpose:\n\n"
            f"[CODE]\n{chunk_stripped}\n[/CODE]"
        )
        
        input_command_raw = get_completion_from_anthropic(
            prompt=user_prompt_to_llm,
            system_prompt=SYSTEM_PROMPT_FOR_INSTRUCTION_GENERATION
        )

        input_command = clean_llm_response(input_command_raw)

        if not input_command:
            logger.warning(f"Skipping chunk {i+1} due to empty or unparseable instruction after cleaning: {chunk_stripped[:50]}...")
            continue
        
        if (len(input_command) + len(chunk_stripped)) > 1500 * 4: 
            logger.warning(f"Skipping chunk {i+1} due to potential max_tokens overflow. Chunk starts with: {chunk_stripped[:50]}...")
            continue
            
        processed_entries.append({
            "messages": [
                {"role": "user", "content": input_command},
                {"role": "assistant", "content": chunk_stripped}
            ]
        })
    
    return processed_entries


def save_processed_id(doc_id: str, filepath: str = PROCESSED_IDS_FILEPATH):
    """
    Saves a single processed document ID to the separate processed_ids file.
    """
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(str(doc_id) + '\n')
        f.flush()
        os.fsync(f.fileno())
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
    logger.info(f"처리된 ID 파일 경로: {PROCESSED_IDS_FILEPATH}")
    logger.info(f"Loaded MONGO_URI_LOAD: {mongo_uri}")
    logger.info(f"Loaded MONGO_DB_LOAD: {db_name}")
    logger.info(f"Loaded MONGO_COLLECTION_LOAD: {collection_name}")
    logger.info(f"Loaded ANTHROPIC_API_KEY (first 5 chars): {ANTHROPIC_API_KEY[:5] if ANTHROPIC_API_KEY else 'N/A'}")

    if not mongo_uri or not db_name or not collection_name or not ANTHROPIC_API_KEY:
        logger.error("One or more critical environment variables (MongoDB URI, DB Name, Collection Name, or Anthropic API Key) are not loaded. Please check your 'mongo.env' file.")
        exit()

    batch_save_jsonl_size = 30 # JSONL 파일에 한 번에 저장할 항목 수

    # 이번 한 번만 새로운 파일에 저장하도록, 타임스탬프 기반의 새 파일명 생성
    # 이후에는 이 변수가 사용되어 해당 파일에만 기록됨
    current_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_jsonl_filename = os.path.join(SCRIPT_DIR, f"instructions_data_run_{current_timestamp}.jsonl")
    logger.info(f"이번 실행의 JSONL 출력 파일 경로: {output_jsonl_filename}")

    # 기존 처리된 ID 목록을 로드합니다.
    current_processed_ids = load_processed_ids(PROCESSED_IDS_FILEPATH)
    
    overall_jsonl_buffer = [] # JSONL에 쓸 데이터를 임시로 저장할 버퍼
    
    # Iterate through documents, skipping processed ones and processing in reverse order
    for doc_index, doc in enumerate(get_docs_sequentially(mongo_uri, db_name, collection_name, batch_fetch_size=100, processed_ids=current_processed_ids)):
        doc_id = str(doc.get('_id'))

        if doc_id in current_processed_ids:
            logger.debug(f"Document {doc_id} (index {doc_index + 1}) was already processed. Skipping LLM call.")
            continue
            
        test_code_content = doc.get('content', '')
        
        if not test_code_content:
            logger.warning(f"Document {doc_id} has no 'content' field. Skipping.")
            save_processed_id(doc_id, PROCESSED_IDS_FILEPATH)
            current_processed_ids.add(doc_id)
            continue
            
        logger.info(f"\n--- Processing Document {doc_id} (First 100 chars) ---")
        logger.info(test_code_content[:100] + "..." if len(test_code_content) > 100 else test_code_content)
        
        newly_processed_entries = process_code_to_jsonl_entries(test_code_content)
        
        if newly_processed_entries:
            overall_jsonl_buffer.extend(newly_processed_entries)
            save_processed_id(doc_id, PROCESSED_IDS_FILEPATH)
            current_processed_ids.add(doc_id)

        # 전체 버퍼가 batch_save_jsonl_size에 도달하면 JSONL에 저장
        # 새 파일이든 기존 파일이든 'a' (append) 모드로 열어 이어씁니다.
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