# 🧠 Data_process

**LLM 학습을 위한 코드 데이터 전처리 파이프라인**  
코드 추출 → 프롬프트 생성 → FIM 학습 데이터 생성까지 자동화

![Status](https://img.shields.io/badge/Status-Active-green)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 🔍 프로젝트 개요

이 프로젝트는 **코드 기반 LLM 학습**을 위한 데이터 전처리 파이프라인입니다.  
다양한 Python 코드 파일을 정제 및 구조화하고, FIM(Fill-in-the-Middle) 학습용 데이터나 프롬프트 기반 학습 데이터를 생성합니다.

> 주로 **Anthropic Claude 스타일 프롬프트**, **OpenAI 방식 FIM**, **MongoDB 연동** 등을 지원합니다.

---

## 🧱 디렉토리 구조

```
Data_process/
├── completion_processing/       # FIM 관련 전처리 스크립트
├── data_preprocess/             # 원시 코드 수집/정제/검증
├── prompt_processing/           # 프롬프트 생성 및 변환
├── jsonl_merge.py               # jsonl 파일 병합 유틸
├── README.md
└── .gitignore
```

---

## ⚙️ 주요 기능

### ✅ 1. 코드 정제 및 전처리
- 주석 제거, 불필요한 개행 제거
- 코드 블록 단위 추출 (`extractcode.py`, `preprocessing.py`)

### ✅ 2. FIM(Fill-in-the-Middle) 학습 데이터 생성
- 중간 토큰 기준 분할
- `prefix` / `target` / `suffix` 구조 생성
- `reformat_fim_data_for_training.py`

### ✅ 3. 프롬프트 포맷팅 (Anthropic 스타일)
- 함수 기반 요약 프롬프트 생성
- 전체 코드 프롬프트 구성
- Pretty JSONL 구성까지 자동 처리

### ✅ 4. MongoDB 적재 및 검증
- `mongo_loader.py` 를 통한 로딩
- 구조적 유효성 검증

---

## 🚀 사용법

```bash
# 환경 설정
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 1. 코드 전처리
python data_preprocess/main.py

# 2. FIM 학습 데이터 생성
python completion_processing/reformat_fim_data_for_training.py

# 3. 프롬프트 변환 예시
python prompt_processing/anthropic_prompt_by_function_from_original_code.py

# 4. JSONL 병합
python jsonl_merge.py
```

> MongoDB 연동 시 `.env` 파일에서 URI를 설정해야 합니다.

---

## 📁 예시 출력 (FIM)

```json
{
  "prefix": "def greet(name):",
  "target": "    print(f\"Hello, {name}\")",
  "suffix": "greet(\"Alice\")"
}
```

---

## 📌 요구사항

- Python 3.10+
- pandas, tqdm, pymongo 등

```bash
pip install -r requirements.txt
```

---

## 🧑‍💻 기여 방법

1. 이슈 또는 PR 등록
2. 코드 스타일 유지
3. 커밋 메시지는 명확하게!

---

## 📝 라이선스

MIT License  
© 2025 Hi-dle Hancom

---
