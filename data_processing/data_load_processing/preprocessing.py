import pandas as pd
import re
import ast # For syntax error checking
import radon.complexity as complexity # For cyclomatic complexity
from radon.metrics import mi_visit # For maintainability index
import io # For line-based operations

# ------------------------------------------------------------------ #
# 1) 보조 함수: 주석 제거 + 특수 문자 비율 계산 + 구문 오류 + 복잡도 계산
# ------------------------------------------------------------------ #
def remove_comments(text: str) -> str:
    """Python 코드 문자열에서 #, ''' ''',  주석 제거"""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"#.*", "", text)                       # 한 줄 주석
    text = re.sub(r'"""(.*?)"""', "", text, flags=re.DOTALL)  # """ 블록
    text = re.sub(r"'''.*?'''", "", text, flags=re.DOTALL)  # ''' 블록
    return text

def special_char_ratio(text: str) -> float:
    if not isinstance(text, str) or not text.strip(): # 빈 문자열, 공백 문자열 처리
        return 1.0 # 특수문자 비율이 높다고 간주 (나쁜 코드)
    specials = re.findall(r"[^a-zA-Z0-9\s]", text) # 알파벳, 숫자, 공백 제외한 모든 문자
    return len(specials) / len(text) if len(text) > 0 else 1.0

def check_syntax_error(code: str) -> bool:
    """Python 코드의 구문 오류 여부 확인"""
    try:
        ast.parse(code)
        return False # 구문 오류 없음
    except SyntaxError:
        return True # 구문 오류 있음
    except Exception: # 기타 파싱 오류 방지
        return True # 오류 발생 시 구문 오류로 간주

def calculate_maintainability_index(code: str) -> float:
    """Radon을 사용하여 유지보수성 지수(MI) 계산"""
    if not isinstance(code, str) or not code.strip():
        return 0.0 # 빈 코드 또는 공백만 있는 경우 0 반환 (낮은 값으로 간주)
    try:
        # mi_visit은 'str' 또는 'ast.Module' 객체를 받음
        # multi=True로 설정하여 여러 함수에 대한 MI 계산 가능하지만, 여기서는 단일 코드 블록으로 가정
        return mi_visit(code, multi=True)
    except Exception: # 구문 오류 등으로 분석 실패 시
        return 0.0 # 계산 실패 시 0 반환 (낮은 값으로 간주)

def calculate_cyclomatic_complexity(code: str) -> float:
    """Radon을 사용하여 순환 복잡도(CC) 계산"""
    if not isinstance(code, str) or not code.strip():
        return 0.0 # 빈 코드 또는 공백만 있는 경우 0 반환 (낮은 값으로 간주)
    try:
        cc_results = complexity.cc_visit(code, multi=True)
        if cc_results:
            # 모든 함수의 CC 합계를 반환하거나, 가장 높은 CC를 반환하거나, 평균을 반환할 수 있음.
            # 여기서는 모든 함수의 CC 합계를 반환
            return sum(c.complexity for c in cc_results)
        return 0.0
    except Exception: # 구문 오류 등으로 분석 실패 시
        return 0.0 # 계산 실패 시 0 반환

# --- 새로운 보조 함수 추가 ---

def extract_code_structure_info(code: str) -> dict:
    """
    Python 코드를 파싱하여 함수 및 클래스 정의, 임포트 정보를 추출합니다.
    """
    info = {
        "function_definitions": [],
        "class_definitions": [],
        "imports": [],
        "has_docstrings": False, # 파일 전체에 docstring이 있는 경우 (모듈 독스트링)
        "number_of_lines": 0,
        "comment_ratio": 0.0
    }
    
    if not isinstance(code, str) or not code.strip():
        return info

    lines = code.splitlines()
    info["number_of_lines"] = len(lines)
    
    comment_lines = 0
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith('#') or \
           stripped_line.startswith('"""') or \
           stripped_line.startswith("'''"):
            comment_lines += 1
    
    if info["number_of_lines"] > 0:
        info["comment_ratio"] = comment_lines / info["number_of_lines"]

    try:
        tree = ast.parse(code)
        
        # 모듈 독스트링 확인
        if (isinstance(tree.body[0], ast.Expr) and 
            isinstance(tree.body[0].value, (ast.Str, ast.Constant)) and 
            isinstance(tree.body[0].value.s, str)):
            info["has_docstrings"] = True

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    "name": node.name,
                    "lineno": node.lineno,
                    "end_lineno": node.end_lineno,
                    "has_docstring": ast.get_docstring(node) is not None
                }
                info["function_definitions"].append(func_info)
            elif isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "lineno": node.lineno,
                    "end_lineno": node.end_lineno,
                    "bases": [b.id if isinstance(b, ast.Name) else None for b in node.bases],
                    "has_docstring": ast.get_docstring(node) is not None
                }
                info["class_definitions"].append(class_info)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if isinstance(node, ast.Import):
                        info["imports"].append(alias.name)
                    else: # ast.ImportFrom
                        module = node.module if node.module else ""
                        level_prefix = "." * node.level
                        full_import = f"{level_prefix}{module}.{alias.name}" if alias.name else f"{level_prefix}{module}"
                        info["imports"].append(full_import)
    except SyntaxError:
        # 구문 오류가 있는 코드는 AST 파싱이 불가능하므로, 이 정보는 비워둠.
        pass
    except Exception:
        # 다른 파싱 오류 처리
        pass

    return info


# ------------------------------------------------------------------ #
# 2) 1차 전처리 (결측치, 길이 0 제거)
# ------------------------------------------------------------------ #
def preprocess_rule_1(df: pd.DataFrame) -> pd.DataFrame:
    if "content" not in df.columns:
        raise KeyError("'content' 컬럼이 없습니다.")

    # 원본 content 길이 계산
    df["original_content_length"] = df["content"].apply(
        lambda x: len(x) if isinstance(x, str) else 0
    )

    # 결측값 및 길이 0인 데이터 제거
    df = df.dropna(subset=["content"]).query("original_content_length > 0").reset_index(drop=True)
    print(f"[INFO] 1차 전처리 (결측치, 길이 0 제거) 후 데이터 개수: {len(df)}")
    return df


# ------------------------------------------------------------------ #
# 3) 2차 전처리 (중복 제거, 특수문자 비율, 구문 오류, 복잡도 지표 추가)
# ------------------------------------------------------------------ #
def preprocess_rule_2(df: pd.DataFrame, min_len: int = 10) -> pd.DataFrame:
    # 중복 content 제거
    df = df.drop_duplicates(subset=["content"]).reset_index(drop=True)
    print(f"[INFO] 중복 제거 후 데이터 개수: {len(df)}")

    # 특수문자 비율 계산 (필터링은 pipeline에서 'bad' 레이블링 단계에서 수행)
    df["special_ratio"] = df["content"].apply(special_char_ratio) # 이전에 주석 처리된 부분을 다시 활성화

    # 주석 제거한 텍스트와 길이 재계산
    df["clean_content"] = df["content"].apply(remove_comments)
    df["content_length"] = df["clean_content"].apply(len) # 주석 제거 후 길이

    # 구문 오류 여부 컬럼 추가
    df["is_syntax_error"] = df["clean_content"].apply(check_syntax_error)

    # 유지보수성 지수(MI) 컬럼 추가
    df["maintainability_index"] = df["content"].apply(calculate_maintainability_index)

    # 순환 복잡도(CC) 컬럼 추가
    df["cyclomatic_complexity"] = df["content"].apply(calculate_cyclomatic_complexity)

    # --- 새로운 컬럼들 추가 ---
    print("[INFO] 코드 구조 및 문서화 관련 지표 추출 중...")
    structure_info = df["content"].apply(extract_code_structure_info)
    
    df["function_definitions"] = structure_info.apply(lambda x: x["function_definitions"])
    df["class_definitions"] = structure_info.apply(lambda x: x["class_definitions"])
    df["imports"] = structure_info.apply(lambda x: x["imports"])
    df["has_module_docstring"] = structure_info.apply(lambda x: x["has_docstrings"]) # 이름 변경
    df["number_of_lines"] = structure_info.apply(lambda x: x["number_of_lines"])
    df["comment_ratio"] = structure_info.apply(lambda x: x["comment_ratio"])

    # 최종 길이 필터링 (너무 짧은 코드는 여기서도 걸러낼 수 있음, 또는 'bad' 레이블링에만 사용)
    # 현재는 'bad' 레이블링에 포함시키므로 여기서는 최소한의 길이만 보장
    df = df[df["content_length"] >= min_len].reset_index(drop=True)
    print(f"[INFO] 2차 전처리 (추가 지표 포함) 후 데이터 개수: {len(df)}")

    return df