import json
import random
import ast
import textwrap

# --- DeepSeekCoder의 FIM 토큰 (정확한 유니코드 문자 확인 필수!) ---
# 실제 모델의 tokenizer.json 파일에서 exact 값을 가져와야 합니다.
# 예시에서는 DeepSeekCoder 논문(arXiv:2401.14196)의 PSM 훈련 형식을 따릅니다.
FIM_START = "<|fim_start|>"
FIM_HOLE = "<|fim_hole|>"
FIM_END = "<|fim_end|>"
EOS_TOKEN = "<|eos_token|>" # 또는 모델의 EOS 토큰 (DeepSeek은 보통 <|EOT|>를 사용)

# --- 코드 파싱 및 분할 헬퍼 함수 ---
def extract_top_level_functions_and_classes(code_content):
    """
    Python 코드에서 최상위 함수와 클래스를 개별 코드 유닛으로 추출합니다.
    """
    tree = ast.parse(code_content)
    code_units = []
    
    for node in ast.walk(tree): # ast.walk를 사용하여 모든 노드를 탐색
        # 함수, 비동기 함수, 클래스 정의 노드만 추출
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            try:
                # Python 3.9+ 호환
                unit_code = ast.get_source_segment(code_content, node)
                if unit_code:
                    code_units.append(unit_code)
            except AttributeError:
                # Python 3.8 이하 호환성을 위한 대체 로직
                # 정확한 들여쓰기와 주석 유지가 어려울 수 있습니다.
                # 원본 코드의 줄 번호로 직접 슬라이싱하는 것이 더 좋습니다.
                lines = code_content.splitlines()
                # ast 노드의 lineno와 end_lineno는 1-based 인덱스
                unit_lines = lines[node.lineno - 1 : node.end_lineno]
                # 들여쓰기를 제거하여 코드를 재구성
                code_units.append(textwrap.dedent("\n".join(unit_lines)))
    
    # 추출된 유닛 중 빈 문자열이 아닌 것만 필터링하여 반환
    return [unit for unit in code_units if unit.strip()]

# --- 오류 주입 헬퍼 함수 ---
def inject_random_error(code_str):
    """
    주어진 코드 문자열에 무작위로 오류를 주입하고, 오류 메시지를 반환합니다.
    (이 함수는 예시이며, 실제로는 더 다양한 오류 주입 로직과 정교한 검증이 필요합니다.)
    """
    lines = code_str.splitlines()
    if not lines:
        return code_str, "오류 없음"

    error_type = random.choice([
        "indentation", "typo_var", "syntax_missing_colon",
        "wrong_library_call", "undeclared_var"
    ])
    
    # 오류를 주입할 라인 선택 (빈 라인이나 주석 라인 제외)
    valid_lines_indices = [i for i, line in enumerate(lines) if line.strip() and not line.strip().startswith('#')]
    if not valid_lines_indices:
        return code_str, "오류 없음" # 주입할 유효한 라인이 없음

    error_line_idx = random.choice(valid_lines_indices)
    original_line = lines[error_line_idx]
    
    corrupted_lines = list(lines)
    error_message = ""

    if error_type == "indentation":
        corrupted_lines[error_line_idx] = "    " + original_line.lstrip() # 임의로 들여쓰기 추가
        error_message = "IndentationError: unexpected indent. 들여쓰기 오류가 발생했습니다."
    elif error_type == "typo_var":
        words = original_line.split()
        if len(words) > 1 and "def" not in words[0] and "class" not in words[0]:
            target_word_idx = random.randint(0, len(words) - 1)
            original_word = words[target_word_idx]
            if len(original_word) > 2:
                corrupted_word = original_word[:-1] + original_word[-1] * 2 # 마지막 문자 반복 오타
                words[target_word_idx] = corrupted_word
                corrupted_lines[error_line_idx] = " ".join(words)
                error_message = f"NameError: name '{corrupted_word}' is not defined. 변수 이름에 오타가 있는 것 같습니다."
            else:
                return code_str, "오류 없음"
        else:
            return code_str, "오류 없음"
    elif error_type == "syntax_missing_colon":
        if original_line.strip().startswith(("if ", "for ", "while ", "def ", "class ")):
            if ":" in original_line:
                corrupted_lines[error_line_idx] = original_line.replace(":", "", 1)
                error_message = "SyntaxError: invalid syntax. 구문 오류 (콜론 누락)가 발생했습니다."
            else:
                return code_str, "오류 없음"
        else:
            return code_str, "오류 없음"
    elif error_type == "wrong_library_call":
        if "import os" in code_str and "os.path.join" in code_str: # os 모듈과 해당 함수가 사용되었다고 가정
            corrupted_code = code_str.replace("os.path.join", "os.join", 1) # 'os.path.join'을 'os.join'으로 변경
            if corrupted_code != code_str:
                return corrupted_code, "AttributeError: module 'os' has no attribute 'join'. 잘못된 라이브러리 함수 호출 오류입니다."
            else:
                return code_str, "오류 없음"
        else:
            return code_str, "오류 없음"
    elif error_type == "undeclared_var":
        # 적절한 위치에 미선언 변수 사용 라인 추가
        insertion_idx = random.randint(0, len(corrupted_lines))
        corrupted_lines.insert(insertion_idx, "    print(some_undefined_variable)") # 임의의 들여쓰기
        error_message = "NameError: name 'some_undefined_variable' is not defined. 선언되지 않은 변수를 사용했습니다."
    
    corrupted_code_str = "\n".join(corrupted_lines)
    
    try: # 구문 오류는 그대로 둠
        ast.parse(corrupted_code_str)
    except SyntaxError:
        pass

    if not error_message:
        return code_str, "오류 없음"
        
    return corrupted_code_str, error_message

# --- 멀티턴 시나리오 생성 함수들 ---
def create_error_fix_multi_turn(original_code_unit):
    """오류 주입 및 수정 멀티턴 시나리오를 생성합니다."""
    corrupted_code, error_message = inject_random_error(original_code_unit)

    if error_message == "오류 없음":
        return None

    messages = [
        {"role": "system", "content": "당신은 Python 코드 디버깅 전문가입니다. 사용자의 오류 보고에 따라 코드를 수정합니다."},
        {"role": "user", "content": f"이 코드를 실행했더니 다음 오류가 발생했습니다. 수정된 코드를 제공해 주세요:\n\n```python\n{corrupted_code}\n```\n\n**오류 메시지:**\n{error_message}"},
        {"role": "assistant", "content": f"네, 말씀하신 오류를 수정했습니다. 다음은 올바른 코드입니다:\n\n```python\n{original_code_unit}\n```"}
    ]
    return {"messages": messages}

def create_function_composition_multi_turn(func_a_code, func_b_code):
    """함수 복합 적용 멀티턴 시나리오를 생성합니다."""
    # 간단한 함수 이름 추출 로직 (매우 간단하므로 완벽하지 않을 수 있습니다.)
    func_a_name = func_a_code.split('(')[0].replace('def ', '').strip()
    func_b_name = func_b_code.split('(')[0].replace('def ', '').strip()

    messages = [
        {"role": "system", "content": "당신은 Python 함수 작성 전문가입니다. 요청에 따라 함수를 만들고 조합합니다."},
        {"role": "user", "content": f"두 숫자를 더하는 Python 함수 `{func_a_name}`를 작성해 주세요."},
        {"role": "assistant", "content": f"```python\n{func_a_code}\n```"},
        {"role": "user", "content": f"이제 숫자의 리스트를 받아 평균을 계산하는 함수 `{func_b_name}`를 작성해 주세요."},
        {"role": "assistant", "content": f"```python\n{func_b_code}\n```"},
        {"role": "user", "content": f"좋아요. 이제 `{func_a_name}` 함수와 `{func_b_name}` 함수를 모두 사용하여,\n\n1. 세 숫자를 더한 후\n2. 그 결과와 다른 숫자 두 개를 합쳐 총 세 숫자의 평균을 계산하는\n\n새로운 함수 `calculate_combined`를 만들어주세요. 즉, `{func_a_name}` 결과에 나머지 두 숫자를 더한 후 `{func_b_name}`을 사용해 평균을 내는 방식입니다."},
        {"role": "assistant", "content": f"네, 요청하신 대로 두 함수를 결합한 `{func_a_name}` 함수와 `{func_b_name}` 함수를 활용하여 `calculate_combined` 함수를 작성했습니다:\n\n```python\n{func_a_code}\n\n{func_b_code}\n\ndef calculate_combined(num1, num2, num3, extra_num1, extra_num2):\n    # func_a_name을 사용하여 세 숫자를 더합니다.\n    sum_of_three = {func_a_name}(num1, {func_a_name}(num2, num3))\n    \n    # 평균 계산을 위해 모든 숫자를 리스트에 넣습니다.\n    all_numbers = [sum_of_three, extra_num1, extra_num2]\n    \n    # func_b_name을 사용하여 평균을 계산합니다.\n    _, combined_average = {func_b_name}(all_numbers)\n    \n    return combined_average\n```"}
    ]
    return {"messages": messages}

def create_fim_scenario_from_unit(code_unit):
    """FIM 시나리오를 생성합니다."""
    lines = code_unit.splitlines()
    if len(lines) < 3: return None

    # FIM 홀을 만들기에 적합한 코드 블록 찾기 (예: 함수 본문)
    if lines[0].strip().startswith("def ") or lines[0].strip().startswith("class "):
        first_line = lines[0]
        body_lines = lines[1:] # 첫 줄을 제외한 나머지
        if not body_lines: return None # 본문이 없으면 FIM 생성 불가

        # 본문 내에서 임의의 FIM 홀 생성
        body_content = "\n".join(body_lines)
        if len(body_content) < 20: # 너무 짧은 본문은 전체를 타겟으로
            prefix = first_line + "\n"
            target = body_content
            suffix = ""
        else:
            split_idx = random.randint(0, len(body_content) - 1)
            # FIM 홀의 크기를 무작위로 결정
            hole_length = random.randint(len(body_content) // 4, len(body_content) // 2) 
            end_idx = min(split_idx + hole_length, len(body_content))
            
            prefix = first_line + "\n" + body_content[:split_idx]
            target = body_content[split_idx:end_idx]
            suffix = body_content[end_idx:]

    else: # 일반 코드 블록의 FIM
        split1 = random.randint(0, len(lines) // 2)
        split2 = random.randint(split1 + 1, len(lines))
        prefix = "\n".join(lines[:split1]) + "\n"
        target = "\n".join(lines[split1:split2])
        suffix = "\n".join(lines[split2:]) + "\n"

    # 최종 FIM 컴포넌트 정리
    prefix = prefix.strip()
    target = target.strip()
    suffix = suffix.strip()

    if not target: return None

    fim_assistant_content = (
        f"{FIM_START}{prefix}{FIM_HOLE}{suffix}{FIM_END}{target}{EOS_TOKEN}"
    )
    user_request_code = f"```python\n{prefix}\n# (Please complete the code here)\n{suffix}\n```"
    user_request = f"Please complete the blank part of the following Python code:\n\n{user_request_code}"

    messages = [
    {"role": "system", "content": "You are an expert in Python code completion. Please accurately fill in the blank part of the given code."},
    {"role": "user", "content": user_request},
    {"role": "assistant", "content": fim_assistant_content}
]
    return {"messages": messages}

def load_codes_from_jsonl_content_field(jsonl_filepath, content_field='content'):
    """
    JSONL 파일에서 'content' 필드에 담긴 코드 내용을 로드합니다.
    """
    codes = []
    with open(jsonl_filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f):
            try:
                data = json.loads(line.strip())
                code_content = data.get(content_field)
                if code_content and isinstance(code_content, str):
                    codes.append(code_content)
                else:
                    print(f"Warning: Line {line_num + 1} has no '{content_field}' field or its value is not a string. Skipping.")
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON on line {line_num + 1}: {e} - Skipping.")
            except Exception as e:
                print(f"An unexpected error occurred on line {line_num + 1}: {e} - Skipping.")
    return codes

def generate_finetuning_data(
    input_jsonl_path, output_jsonl_path,
    fim_ratio=0.4, error_ratio=0.3, complex_func_ratio=0.3
):
    """
    JSONL 파일 내의 'content' 컬럼에서 코드들을 읽어 DeepSeekCoder 파인튜닝 데이터셋을 생성합니다.
    """
    all_raw_codes = load_codes_from_jsonl_content_field(input_jsonl_path, content_field='content')
    
    all_code_units = []
    for i, raw_code_content in enumerate(all_raw_codes):
        if not raw_code_content.strip(): continue
        try:
            # 각 원본 코드 문자열에서 함수/클래스 유닛 추출
            units = extract_top_level_functions_and_classes(raw_code_content)
            all_code_units.extend(units)
            print(f"원본 JSONL 레코드 {i+1}에서 {len(units)}개의 코드 유닛을 추출했습니다.")
        except SyntaxError as e:
            print(f"Warning: Syntax error in code block from record {i+1}. Skipping unit extraction: {e}")
        except Exception as e:
            print(f"Error processing code block from record {i+1}: {e}")
    
    if not all_code_units:
        print("추출된 코드 유닛이 없습니다. 스크립트를 종료합니다.")
        return

    generated_data = []
    random.shuffle(all_code_units)

    num_fim = 0
    num_error = 0
    num_complex = 0

    for i, unit_code in enumerate(all_code_units):
        if not unit_code.strip(): continue

        # FIM 시나리오 생성
        if random.random() < fim_ratio:
            fim_scenario = create_fim_scenario_from_unit(unit_code)
            if fim_scenario:
                generated_data.append(fim_scenario)
                num_fim += 1

        # 오류 수정 시나리오 생성
        if random.random() < error_ratio:
            error_scenario = create_error_fix_multi_turn(unit_code)
            if error_scenario:
                generated_data.append(error_scenario)
                num_error += 1
        
        # 함수 복합 적용 시나리오 생성 (최소 두 개의 함수 유닛이 필요)
        if random.random() < complex_func_ratio and len(all_code_units) >= 2:
            try:
                # 무작위로 다른 함수 두 개를 선택하여 조합 시도
                selected_funcs = random.sample(all_code_units, 2)
                func_a_candidate = selected_funcs[0]
                func_b_candidate = selected_funcs[1]

                # 함수 정의인지, 너무 짧지 않은지 확인
                if func_a_candidate.strip().startswith("def ") and \
                   func_b_candidate.strip().startswith("def ") and \
                   func_a_candidate != func_b_candidate and \
                   len(func_a_candidate.splitlines()) > 5 and len(func_b_candidate.splitlines()) > 5:
                    
                    complex_scenario = create_function_composition_multi_turn(func_a_candidate, func_b_candidate)
                    if complex_scenario:
                        generated_data.append(complex_scenario)
                        num_complex += 1
            except ValueError: # random.sample 에러 방지 (요소 부족)
                pass
            except Exception as e:
                print(f"Error generating complex function scenario: {e}")

    # 생성된 데이터를 JSONL 파일로 저장
    with open(output_jsonl_path, 'w', encoding='utf-8') as outfile:
        for entry in generated_data:
            outfile.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f"\n--- 데이터 생성 완료 ---")
    print(f"총 {len(generated_data)}개의 멀티턴 데이터가 '{output_jsonl_path}'에 저장되었습니다.")
    print(f"  - FIM 시나리오: {num_fim}개")
    print(f"  - 오류 수정 시나리오: {num_error}개")
    print(f"  - 함수 복합 적용 시나리오: {num_complex}개")
    print("\n생성된 데이터를 반드시 열어 내용을 검토하고, 특히 assistant의 '정답' 부분이 올바른지 확인해야 합니다.")
    print("오류 주입 및 함수 복합 로직은 매우 복잡하므로, 수동 검토 및 수정이 필수적입니다.")


# --- 스크립트 실행 예시 ---
if __name__ == "__main__":
    # 사용 방법:
    # 1. 'my_original_codes_input.jsonl' 파일을 스크립트와 같은 경로에 준비합니다.
    #    이 파일은 각 라인이 {"content": "파이썬 코드 원본"} 형식이어야 합니다.
    #    예시:
    #    {"content": "def func1(a, b):\n    return a + b"}
    #    {"content": "class MyUtil:\n    def __init__(self, val):\n        self.val = val"}
    #
    # 2. 아래 'input_jsonl_filename'과 'output_jsonl_filename'을 필요에 따라 수정합니다.
    #
    # 3. 스크립트를 실행합니다: python your_script_name.py

    input_jsonl_filename = "data.jsonl"
    output_jsonl_filename = "prompt.jsonl"

    print(f"입력 JSONL 파일: '{input_jsonl_filename}'에서 코드를 읽어옵니다.")
    print(f"출력 JSONL 파일: '{output_jsonl_filename}'에 데이터를 저장합니다.")

    # 데이터 생성 함수 호출
    generate_finetuning_data(
        input_jsonl_path=input_jsonl_filename,
        output_jsonl_path=output_jsonl_filename,
        fim_ratio=0.4,       # FIM 시나리오 생성 확률
        error_ratio=0.3,     # 오류 수정 시나리오 생성 확률
        complex_func_ratio=0.3 # 함수 복합 적용 시나리오 생성 확률
    )