import json
import re
import random

def split_code_into_function_chunks(code_str, max_lines_per_chunk=30):
    """
    코드 문자열을 함수/클래스 단위 등 큰 기능 단위로 나누고,
    각 기능 내에서 max_lines_per_chunk 기준으로 더 작은 청크로 분할.
    """
    lines = code_str.splitlines()
    
    # 1. 함수/클래스 시작 라인 인덱스 찾기
    func_start_idxs = []
    pattern = re.compile(r'^\s*(def|class)\s+[\w_]+\s*\(?.*\)?:')
    for i, line in enumerate(lines):
        if pattern.match(line):
            func_start_idxs.append(i)
    func_start_idxs.append(len(lines))  # 마지막 끝 인덱스
    
    chunks = []
    for idx in range(len(func_start_idxs)-1):
        start = func_start_idxs[idx]
        end = func_start_idxs[idx+1]
        func_lines = lines[start:end]

        # func_lines가 max_lines_per_chunk보다 크면 분할
        for i in range(0, len(func_lines), max_lines_per_chunk):
            chunk_lines = func_lines[i:i+max_lines_per_chunk]
            chunk_str = "\n".join(chunk_lines).strip()
            if chunk_str:
                chunks.append(chunk_str)
    
    # 함수/클래스 없는 부분 (0 ~ 첫 함수 시작 전)
    if func_start_idxs and func_start_idxs[0] > 0:
        header_lines = lines[:func_start_idxs[0]]
        header_chunk = "\n".join(header_lines).strip()
        if header_chunk:
            chunks.insert(0, header_chunk)

    # 함수/클래스가 전혀 없으면 전체 코드가 하나의 청크
    if not func_start_idxs or len(func_start_idxs) == 1:
        full_code = "\n".join(lines).strip()
        if full_code:
            chunks = [full_code]

    return chunks

def convert_jsonl_to_fim_format_with_limit(input_jsonl_path, output_jsonl_path,
                                           max_chunks_per_file=5,
                                           max_lines_per_chunk=30,
                                           min_prefix_suffix_lines=3):
    """
    JSONL 파일을 읽어, 코드 청크를 기능 단위로 분할하고,
    파일당 최대 청크 수를 제한해서 FIM 학습용 JSONL 생성.
    """
    with open(input_jsonl_path, 'r', encoding='utf-8') as infile, \
         open(output_jsonl_path, "w", encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            try:
                obj = json.loads(line)
                content = obj.get("content", "")
                if not content.strip():
                    continue

                content = content.replace('\\/', '/')
                lines = content.splitlines()
                
                # 1. 기능 단위 청크 분할
                chunks = split_code_into_function_chunks(content, max_lines_per_chunk=max_lines_per_chunk)
                
                # 2. 파일당 최대 청크 수 제한 (무작위 선택)
                if len(chunks) > max_chunks_per_file:
                    chunks = random.sample(chunks, max_chunks_per_file)

                # 3. 각 청크별로 prefix, middle, suffix 나누기
                # prefix: 전체 코드에서 청크 앞부분, suffix: 뒷부분, middle: 청크 내용
                current_start_line_idx = 0
                full_code_lines = lines
                for chunk in chunks:
                    chunk_lines = chunk.splitlines()

                    # chunk가 전체 코드에서 어디에 위치하는지 찾기
                    found = False
                    search_start = current_start_line_idx
                    while search_start < len(full_code_lines):
                        match = True
                        for j in range(len(chunk_lines)):
                            if search_start + j >= len(full_code_lines) or \
                               full_code_lines[search_start + j] != chunk_lines[j]:
                                match = False
                                break
                        if match:
                            current_start_line_idx = search_start
                            found = True
                            break
                        search_start += 1
                    
                    if not found:
                        print(f"[Warning][Line {line_num}] Chunk not found in full content. Skipping.")
                        continue

                    prefix_lines = full_code_lines[:current_start_line_idx]
                    suffix_lines = full_code_lines[current_start_line_idx + len(chunk_lines):]

                    # prefix, suffix가 너무 짧으면 skip
                    if len(prefix_lines) < min_prefix_suffix_lines or len(suffix_lines) < min_prefix_suffix_lines:
                        continue

                    prefix_code = "\n".join(prefix_lines).strip()
                    middle_code = chunk.strip()
                    suffix_code = "\n".join(suffix_lines).strip()

                    fim_obj = {
                        "prefix_code": prefix_code,
                        "target_code": middle_code,
                        "suffix_code": suffix_code
                    }
                    outfile.write(json.dumps(fim_obj, ensure_ascii=False) + "\n")
                
                print(f"[Line {line_num}] Processed {len(chunks)} chunks.")
            
            except json.JSONDecodeError as e:
                print(f"[Line {line_num}] JSONDecodeError: {e}")
            except Exception as e:
                print(f"[Line {line_num}] Unexpected error: {e}")

if __name__ == "__main__":
    input_path = "data.jsonl"
    output_path = "fim_output_limited.jsonl"
    convert_jsonl_to_fim_format_with_limit(input_path, output_path)
