<h1 align="center">🧠 Data_process</h1>
<p align="center">
  <i>코드 기반 LLM 학습을 위한 End-to-End 데이터 처리 파이프라인</i><br>
  <b>Code Crawling ➝ Preprocessing ➝ Prompt / FIM Sample ➝ MongoDB Upload</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" />
</p>

---

## ✨ 프로젝트 소개

이 저장소는 <b>DeepSeek Coder 6.7B</b>와 같은 코드 특화 LLM 학습을 위해 대규모 코드 데이터를 정제하고 구조화하는 파이프라인입니다.  
다양한 소스에서 수집한 Python 코드들을 FIM 학습 포맷 및 프롬프트 기반 구조로 자동 변환하고, 필요시 MongoDB에 저장까지 처리합니다.

> 🧩 Anthropic Claude 스타일 프롬프트, 🔧 OpenAI FIM 구조, ☁️ Mongo 연동 등 다양한 학습 구조 지원

---

## 📁 디렉토리 구조

```
Data_process/
├── comment_processing/         # 주석 데이터 생성
│   └── comment.py
├── completion_processing/      # 자동완성 데이터 생성
│   ├── codetolongfim.py
│   ├── codetoshortfim.py
│   ├── move_import.py
│   └── reformat_fim_data_for_training.py
├── data_processing/            # 코드 전처리 및 Mongo 적재
│   ├── extractcode.py
│   └── data_load_process/
│       ├── main.py
│       ├── preprocessing.py
│       ├── pipeline.py
│       ├── ml_validation.py
│       └── mongo_loader.py
├── error_processing/           # 오류 데이터 로드 및 생성
│   ├── error.py
│   └── crawlers/
│       ├── betterstack3.py
│       ├── geeksforgeeks.py
│       ├── official_exceptions.py
│       ├── rollbar.py
│       └── tutorialsteacher.py
├── prompt_processing/          # Claude 기반 명령 데이터 생성
│   ├── anthropic_prompt_by_function_from_original_code.py
│   ├── anthropic_prompt_by_whole_code.py
│   ├── jsonl_code_extractor.py
│   ├── jsonl_pretty_dialogue_formatter.py
│   ├── enter_remove.py
│   └── merge_jsonl.py
├── jsonl_merge.py              # JSONL 파일 병합 스크립트
├── requirements.txt
└── README.md
```

---

## ⚙️ 주요 기능

| ✅ 기능            | 설명                                                                                          |
| ------------------ | --------------------------------------------------------------------------------------------- |
| 코드 전처리        | 주석 제거, 공백 제거, 블록 단위 추출 (`extractcode.py`)                                       |
| FIM 데이터 생성    | `prefix`, `target`, `suffix` 구조화 (`codetolongfim.py`, `reformat_fim_data_for_training.py`) |
| 프롬프트 포맷팅    | Claude 스타일 요약 및 전체 코드 프롬프트 생성                                                 |
| JSONL 병합 및 정리 | 대용량 데이터 생성 및 병합 (`jsonl_merge.py`, `merge_jsonl.py`)                               |
| MongoDB 적재       | `.env` 기반 Mongo URI 연결 및 유효성 검증 (`mongo_loader.py`)                                 |
| 에러 예제 수집     | 공식 문서 및 커뮤니티 기반 에러 사례 크롤링                                                   |

---

## 🚀 빠른 시작

```bash
# 1. 가상환경 생성 및 의존성 설치
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 원시 코드 전처리
python data_processing/data_load_process/main.py

# 3. FIM 학습 데이터 생성
python completion_processing/reformat_fim_data_for_training.py

# 4. Claude 스타일 프롬프트 생성
python prompt_processing/anthropic_prompt_by_function_from_original_code.py

# 5. JSONL 병합
python jsonl_merge.py

# 6. MongoDB 적재
python data_processing/data_load_process/mongo_loader.py
```

> `.env` 파일에 `MONGO_URI=your_uri_here` 를 설정해 주세요.

---

## 🧪 FIM 출력 예시

```json
{
  "prefix": "def multiply(a, b):",
  "target": "    return a * b",
  "suffix": "print(multiply(2, 3))"
}
```

---

## 📦 요구사항

- Python >= 3.10
- 주요 패키지: `pandas`, `tqdm`, `pymongo`, `python-dotenv`, `ast`, 등

```bash
pip install -r requirements.txt
```

---

## 📌 특징 요약

- 🔄 End-to-End 파이프라인 구성
- ✍️ 다양한 프롬프트 스타일 지원
- 🧠 LLM 학습용 데이터 구조에 최적화
- ☁️ MongoDB 기반 대용량 적재 가능
- 🛠 확장 가능한 구조와 모듈 분리

---

<p align="center"><i>Made with ❤️ for Large Language Model Coders</i></p>
