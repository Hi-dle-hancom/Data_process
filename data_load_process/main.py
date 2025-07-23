# main.py

from pipeline import run_pipeline
import os
import pandas as pd
from dotenv import load_dotenv

if __name__ == "__main__":
    # .env 파일에서 환경 변수를 로드합니다.
    load_dotenv(dotenv_path="mongo1.env") # .env 로드

    # MongoDB 데이터 로드용 URI
    mongo_uri_load = os.getenv("MONGO_URI_LOAD")
    db_name_load = os.getenv("MONGO_DB_LOAD")
    collection_name_load = os.getenv("MONGO_COLLECTION_LOAD")

    # MongoDB Atlas 데이터 저장용 URI
    mongo_uri_save = os.getenv("MONGO_URI_SAVE")
    db_name_save = os.getenv("MONGO_DB_SAVE")
    good_collection_name = os.getenv("MONGO_GOOD_COLLECTION")
    bad_collection_name = os.getenv("MONGO_BAD_COLLECTION")

    # JSONL 파일 이름
    output_jsonl = os.getenv("OUTPUT_GOOD_JSONL_FILE", "train.jsonl") # 기본값 설정
    output_bad_jsonl = os.getenv("OUTPUT_BAD_JSONL_FILE", "bad_data.jsonl") # 기본값 설정

    # 전처리 최소 콘텐츠 길이 (선택 사항)
    min_content_length_for_preprocessing = int(os.getenv("MIN_CONTENT_LENGTH", 10))

    # 데이터 로드 개수 제한 (새로 추가된 부분)
    data_load_limit = int(os.getenv("DATA_LOAD_LIMIT", 0)) # mongo.env에서 설정한 값 가져오기

    # 환경 변수가 제대로 로드되었는지 확인 (필수)
    # min_content_length_for_preprocessing와 data_load_limit는 기본값이 있으므로 제외
    required_vars = {
        "MONGO_URI_LOAD": mongo_uri_load,
        "MONGO_DB_LOAD": db_name_load,
        "MONGO_COLLECTION_LOAD": collection_name_load,
        "MONGO_URI_SAVE": mongo_uri_save,
        "MONGO_DB_SAVE": db_name_save,
        "MONGO_GOOD_COLLECTION": good_collection_name,
        "MONGO_BAD_COLLECTION": bad_collection_name
    }
    missing_vars = [
        key for key, val in required_vars.items() if val is None
    ]
    if missing_vars:
        print(f"[ERROR] 다음 환경 변수들이 mongo.env에 설정되지 않았습니다: {', '.join(missing_vars)}")
        exit(1)

    # None이 아님을 보장하므로 str로 캐스팅
    mongo_uri_load = str(mongo_uri_load)
    db_name_load = str(db_name_load)
    collection_name_load = str(collection_name_load)
    mongo_uri_save = str(mongo_uri_save)
    db_name_save = str(db_name_save)
    good_collection_name = str(good_collection_name)
    bad_collection_name = str(bad_collection_name)

    print("--- 파이프라인 실행 시작 ---")
    
    # run_pipeline이 반환하는 세 개의 DataFrame을 받도록 수정
    final_data, iso_removed_data, lof_removed_data = run_pipeline( # 반환 변수명 변경
        mongo_uri_load=mongo_uri_load,
        db_name_load=db_name_load,
        collection_name_load=collection_name_load,
        
        mongo_uri_save=mongo_uri_save,
        db_name_save=db_name_save,
        good_collection_name=good_collection_name,
        bad_collection_name=bad_collection_name,
        
        output_jsonl=output_jsonl, # good 데이터 JSONL 파일 경로
        output_bad_jsonl=output_bad_jsonl, # bad 데이터 JSONL 파일 경로 추가
        min_content_length=min_content_length_for_preprocessing,
        data_load_limit=data_load_limit # <-- limit 전달
    )
    print("--- 파이프라인 완료 ---\n")

    # 여기서 반환된 DataFrame들을 사용하여 추가 분석을 수행할 수 있습니다.
    print("--- Main 스크립트에서 최종 분석 ---")
    print(f"최종 필터링을 통과한 굿 데이터 개수: {len(final_data)}")
    print(f"IsolationForest에 의해 제거된 데이터 개수: {len(iso_removed_data)}")
    print(f"LOF에 의해 제거된 데이터 개수: {len(lof_removed_data)}")
    
    # 추가적으로 필요한 분석이나 로깅을 여기에 구현할 수 있습니다.
    # 예: 최종 굿 데이터의 일부 출력
    # print("\n최종 굿 데이터 샘플:")
    # print(final_data.head())