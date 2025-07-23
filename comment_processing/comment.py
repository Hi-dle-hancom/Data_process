import json
import random
import os
import ast
from tqdm import tqdm

# --- Configuration Variables ---
INPUT_JSONL_FILE = "output_good2.jsonl"
TEMPLATE_CONFIG_FILE = "template_config.json"
OUTPUT_JSONL_FILE = "train.jsonl"
TARGET_SAMPLE_COUNT = 80000

# --- Helper Functions ---
def is_valid_python_code(code_str: str) -> bool:
    """Checks if a string is valid Python code."""
    try:
        ast.parse(code_str)
        return True
    except SyntaxError:
        return False

def is_allowed_text(text: str) -> bool:
    """
    Checks if a string contains only allowed characters.
    It allows standard ASCII characters plus the specific special characters
    used in the FIM tags ('<', '>', '｜').
    """
    if not isinstance(text, str):
        return False
    
    allowed_special_chars = {'<', '>', '｜'}
    
    for char in text:
        if ord(char) < 128:
            continue
        if char in allowed_special_chars:
            continue
        return False
    return True

def build_system_prompt(persona: dict) -> str:
    """
    Builds the system prompt from a persona dictionary.
    """
    return (
        f"{persona.get('role_context', 'You are a helpful AI assistant.')} "
        f"{persona.get('tone_context', '')} "
        f"{persona.get('task_instruction', '')} "
        f"{persona.get('output_requirement', '')}"
    ).strip()

# <--- [변경점 1] 함수 이름과 역할 변경 --->
# 이 함수는 이제 단순 FIM 프롬프트뿐만 아니라, 페르소나에 맞는 Assistant 응답까지 생성합니다.
# [수정 필요] Python 스크립트의 이 함수를 아래 코드로 교체하세요.

def create_conversation_pair(snippet: str, persona: dict) -> tuple[str | None, str | None]:
    """
    Creates the user prompt and a persona-aware assistant answer.
    The assistant's answer will include explanations or notes if the persona requires them.
    Returns (None, None) if a meaningful FIM task cannot be created.
    """
    lines = snippet.strip().split('\n')
    
    if len(lines) < 3:
        return None, None

    cut_start_index = random.randint(1, len(lines) - 2)
    cut_end_index = random.randint(cut_start_index, len(lines) - 2)

    prefix_lines = lines[:cut_start_index]
    code_part_lines = lines[cut_start_index : cut_end_index + 1]
    suffix_lines = lines[cut_end_index + 1:]

    prefix = "\n".join(prefix_lines)
    code_part = "\n".join(code_part_lines)
    suffix = "\n".join(suffix_lines)
    
    instruction = "Please complete the missing part of the following Python code snippet:\n\n"
    begin_tag = "<｜fim begin｜>"
    hole_tag = "<｜fim hole｜>"
    end_tag = "<｜fim end｜>"

    user_prompt = f"{instruction}{begin_tag}{prefix}{hole_tag}{suffix}{end_tag}"

    output_req = persona.get('output_requirement', '')
    final_assistant_answer = code_part

    # [업데이트!] 새로운 키워드와 템플릿 추가
    if "--- Explanation ---" in output_req:
        explanation_template = (
            "\n\n--- Explanation ---\n"
            "Of course! Here is the code to complete the snippet. "
            "This part of the code is important because it handles the specific logic needed to continue the program's execution correctly. "
            "Let me know if you have any more questions!"
        )
        final_assistant_answer += explanation_template

    elif "--- Rationale ---" in output_req:
        rationale_template = (
            "\n\n--- Rationale ---\n"
            "I've completed the code following Python best practices. This implementation is both readable and efficient. "
            "I chose this approach over others because it offers better clarity without a significant performance trade-off for this context."
        )
        final_assistant_answer += rationale_template

    elif "--- Notes ---" in output_req:
        notes_template = (
            "\n\n--- Notes ---\n"
            "Here's the completed code. My approach was to fill in the missing logic "
            "while maintaining the existing code style. This implementation is straightforward "
            "and should be efficient enough for our use case. I considered a couple of alternatives, but this seemed the most readable."
        )
        final_assistant_answer += notes_template

    elif "--- Test Coverage ---" in output_req:
        test_coverage_template = (
            "\n\n--- Test Coverage ---\n"
            "The provided test case now covers the primary success path for this function. "
            "Specifically, it asserts that the correct output is returned for a standard set of inputs. "
            "I also added a check for a common edge case to ensure the function is robust."
        )
        final_assistant_answer += test_coverage_template
        
    return user_prompt, final_assistant_answer

# --- Main Logic Function ---
def generate_completed_dataset(input_path: str, config_path: str, output_path: str, target_count: int):
    """
    Generates a completed training dataset, automatically filtering out any
    non-allowed content and examples with empty answers.
    """
    print(f"[INFO] Loading and filtering allowed code snippets from '{input_path}'...")
    valid_snippets = []
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    snippet = data.get("content")
                    if snippet and is_valid_python_code(snippet) and is_allowed_text(snippet):
                        valid_snippets.append(snippet)
                except (json.JSONDecodeError, KeyError):
                    continue
        if not valid_snippets:
            print("[ERROR] No valid (allowed text) code snippets found.")
            return
        print(f"[INFO] Loaded {len(valid_snippets)} valid code snippets.")
    except Exception as e:
        print(f"[ERROR] Failed to load the original file: {e}")
        return

    print(f"[INFO] Loading and filtering allowed personas from '{config_path}'...")
    allowed_personas = []
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            all_personas = json.load(f).get("personas", [])
            for p in all_personas:
                is_allowed = all(is_allowed_text(str(p.get(key, ''))) for key in p)
                if is_allowed:
                    allowed_personas.append(p)
        
        if not allowed_personas:
            print(f"[ERROR] No allowed personas found in '{config_path}'. Please check the file content.")
            return
        print(f"[INFO] Loaded {len(allowed_personas)} allowed personas.")
    except Exception as e:
        print(f"[ERROR] Failed to load the template file: {e}")
        return

    print(f"[INFO] Starting to generate {target_count} completed training examples...")
    
    generated_count = 0
    with open(output_path, "w", encoding="utf-8") as outfile:
        with tqdm(total=target_count, desc="Generating Training Data") as pbar:
            while generated_count < target_count:
                chosen_snippet = random.choice(valid_snippets)
                chosen_persona = random.choice(allowed_personas)

                system_prompt = build_system_prompt(chosen_persona)
                
                # <--- [변경점 3] 수정한 함수를 호출하고, persona를 전달 --->
                user_prompt, assistant_answer = create_conversation_pair(chosen_snippet, chosen_persona)
                
                if user_prompt is None or not assistant_answer or not assistant_answer.strip():
                    continue

                training_record = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                        {"role": "assistant", "content": assistant_answer}
                    ]
                }
                
                json.dump(training_record, outfile, ensure_ascii=False)
                outfile.write("\n")
                
                generated_count += 1
                pbar.update(1)

    print(f"\n🎉 Task complete! {generated_count} high-quality training examples have been saved to '{output_path}'.")

# --- Script Execution ---
if __name__ == "__main__":
    generate_completed_dataset(
        input_path=INPUT_JSONL_FILE,
        config_path=TEMPLATE_CONFIG_FILE,
        output_path=OUTPUT_JSONL_FILE,
        target_count=TARGET_SAMPLE_COUNT
    )