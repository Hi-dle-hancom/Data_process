# pipeline.py

import pandas as pd
from data_processing.data_load_process.mongo_loader import load_data_from_mongo, save_data_to_mongo # save_data_to_mongo 추가
from preprocessing import preprocess_rule_1, preprocess_rule_2 # Updated import
from ml_validation import isolation_filter, lof_filter # IsolationForest, LOF 유지
import os # 파일 존재 여부 확인을 위해 os 모듈 추가

# 데이터 처리 및 모델 학습/추론을 모듈화된 파이프라인 형태로 구성한 파일
# 전체 작업 흐름을 하나로 묶는 “자동 실행 스크립트”

def save_dataframe_to_jsonl_in_chunks(df: pd.DataFrame, file_path: str, chunk_size: int = 1000):
    """
    DataFrame을 지정된 청크 크기만큼 나누어 JSONL 파일에 추가 모드로 저장합니다.
    파일이 존재하지 않으면 새로 생성하고, 첫 번째 청크에만 헤더를 추가합니다.
    """
    if df.empty:
        print(f"[WARN] 저장할 데이터가 없어 '{file_path}'에 저장하지 않습니다.")
        return

    # 파일이 존재하는지 미리 확인하여 헤더 쓰기 여부 결정
    file_exists = os.path.exists(file_path)

    total_chunks = (len(df) + chunk_size - 1) // chunk_size
    saved_count = 0

    print(f"[INFO] '{file_path}'에 데이터 청크 저장 시작 (청크 크기: {chunk_size})...")

    for i in range(total_chunks):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, len(df))
        chunk_df = df.iloc[start_idx:end_idx]

        if not chunk_df.empty:
            # 첫 번째 청크이고 파일이 존재하지 않으면 헤더 포함하여 쓰기
            # 이미 파일이 존재하면 (이전 실행에서 생성되었거나) 헤더 없이 추가
            header = not file_exists and i == 0
            
            # mode='a'는 append 모드, lines=True는 JSONL 형식, force_ascii=False는 한글 깨짐 방지
            chunk_df.to_json(file_path, orient="records", lines=True, force_ascii=False, mode='a')
            saved_count += len(chunk_df)
            file_exists = True # 첫 청크가 저장되면 파일이 존재하게 됨

    print(f"[INFO] '{file_path}'에 총 {saved_count}개 데이터 저장 완료.")


# MongoDB에서 데이터를 로드하고, 전처리 및 ML 검증을 수행하여 JSONL 파일로 저장하는 파이프라인
def run_pipeline(
    mongo_uri_load: str,
    db_name_load: str,
    collection_name_load: str,
    mongo_uri_save: str,
    db_name_save: str,
    good_collection_name: str,
    bad_collection_name: str,
    output_jsonl: str,       # good 데이터용 output_jsonl 이름
    output_bad_jsonl: str,   # bad 데이터용 output_jsonl 이름 추가
    min_content_length: int = 10,
    data_load_limit: int = 0, # <-- limit 인자 추가
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    print("[INFO] MongoDB에서 데이터 로드 중...")
    # load_data_from_mongo 함수에 data_load_limit 전달
    df = load_data_from_mongo(mongo_uri_load, db_name_load, collection_name_load, limit=data_load_limit)
    if df.empty:
        print("[WARN] 로드된 데이터가 없어 파이프라인을 중단합니다.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    original_data_count = len(df)
    print(f"[INFO] 원본 데이터 개수: {original_data_count}")

    # 1차 전처리 (필수 필드 확인, 결측치 제거, 길이 0 제거)
    print("[INFO] 1차 전처리 (필수 필드 확인, 결측치, 길이 0 제거) 진행 중...")
    df_preprocessed_1 = preprocess_rule_1(df)
    if df_preprocessed_1.empty:
        print("[WARN] 1차 전처리 후 데이터가 없어 파이프라인을 중단합니다.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # 2차 전처리 (중복 제거, 구문 오류, 복잡도 지표 추가)
    print("[INFO] 2차 전처리 (중복 제거, 구문 오류, 복잡도 지표 추가) 진행 중...")
    df_preprocessed_2 = preprocess_rule_2(df_preprocessed_1, min_len=min_content_length)
    if df_preprocessed_2.empty:
        print("[WARN] 2차 전처리 후 데이터가 없어 파이프라인을 중단합니다.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # ------------------------------------------------------------------ #
    # 굿/배드 데이터 분리 및 레이블링
    # ------------------------------------------------------------------ #
    print("[INFO] 굿/배드 데이터 분리 및 레이블링 시작...")
    
    # 배드 데이터 조건 정의
    bad_conditions = (
        (df_preprocessed_2['content_length'] < min_content_length) |
        (df_preprocessed_2['is_syntax_error'] == True) |
        (df_preprocessed_2['cyclomatic_complexity'] > 50) | # 복잡도가 너무 높은 코드
        (df_preprocessed_2['maintainability_index'] < 20)    # 유지보수성 지수가 너무 낮은 코드
    )

    bad_data = df_preprocessed_2[bad_conditions].copy()
    good_data = df_preprocessed_2[~bad_conditions].copy()

    # 'label' 컬럼 추가
    good_data['label'] = 1 # 굿 코드
    bad_data['label'] = 0  # 배드 코드
    
    print(f"[INFO] 규칙 기반 분류 후 굿 데이터 개수: {len(good_data)}")
    print(f"[INFO] 규칙 기반 분류 후 배드 데이터 개수: {len(bad_data)}")

    # ------------------------------------------------------------------ #
    # ML 기반 이상치 필터링 (굿 데이터에만 적용)
    # ------------------------------------------------------------------ #
    print("[INFO] ML 기반 이상치 필터링 (IsolationForest, LOF) 시작 (굿 데이터에만 적용)...")

    # IsolationForest 필터링
    filtered_by_iso = isolation_filter(good_data.copy())
    iso_removed_data = good_data[~good_data.index.isin(filtered_by_iso.index)].copy() # ISO에 의해 제거된 데이터

    # LOF 필터링
    final_good_data = lof_filter(filtered_by_iso.copy())
    lof_removed_data = filtered_by_iso[~filtered_by_iso.index.isin(final_good_data.index)].copy() # LOF에 의해 제거된 데이터

    print(f"[INFO] 최종 필터링을 통과한 굿 데이터 개수: {len(final_good_data)}")
    print(f"[INFO] IsolationForest에 의해 제거된 데이터 개수: {len(iso_removed_data)}")
    print(f"[INFO] LOF에 의해 제거된 데이터 개수: {len(lof_removed_data)}")
    
    # 굿 데이터와 배드 데이터 합치기 (필요하다면)
    # final_processed_data = pd.concat([final_good_data, bad_data_cleaned], ignore_index=True)


    # ------------------------------------------------------------------ #
    # MongoDB에 저장 (데이터베이스/컬렉션 분리)
    # ------------------------------------------------------------------ #
    # good_data_cleaned는 최종 필터링된 좋은 데이터
    # bad_data_cleaned는 규칙 기반으로 분류된 나쁜 데이터 + ML 필터링으로 제거된 데이터
    
    # ML 필터링에서 제거된 데이터를 bad_data에 추가
    bad_data_cleaned = pd.concat([bad_data, iso_removed_data, lof_removed_data], ignore_index=True)
    
    # 최종 good_data와 bad_data_cleaned에서 'anomaly_iso', 'anomaly_lof' 컬럼 제거
    if 'anomaly_iso' in final_good_data.columns:
        final_good_data = final_good_data.drop(columns=['anomaly_iso'])
    if 'anomaly_lof' in final_good_data.columns:
        final_good_data = final_good_data.drop(columns=['anomaly_lof'])
    
    if 'anomaly_iso' in bad_data_cleaned.columns:
        bad_data_cleaned = bad_data_cleaned.drop(columns=['anomaly_iso'])
    if 'anomaly_lof' in bad_data_cleaned.columns:
        bad_data_cleaned = bad_data_cleaned.drop(columns=['anomaly_lof'])
    
    print(f"[INFO] 최종 MongoDB에 저장될 굿 데이터 개수: {len(final_good_data)}")
    print(f"[INFO] 최종 MongoDB에 저장될 배드 데이터 개수: {len(bad_data_cleaned)}")

    print("[INFO] MongoDB에 굿 데이터 저장 중...")
    save_data_to_mongo(final_good_data, mongo_uri_save, db_name_save, good_collection_name)
    print("[INFO] MongoDB에 배드 데이터 저장 중...")
    save_data_to_mongo(bad_data_cleaned, mongo_uri_save, db_name_save, bad_collection_name)

    # Good 데이터를 JSONL 파일로 1000개씩 추가 모드로 저장
    print(f"[INFO] 최종 굿 데이터를 {output_jsonl} 파일로 1000개씩 저장 중 (label 컬럼 제외)...\r\n")
    final_good_for_jsonl = final_good_data.copy()
    save_dataframe_to_jsonl_in_chunks(final_good_for_jsonl, output_jsonl, chunk_size=1000)
    print(f"[INFO] JSONL 저장 완료: {output_jsonl} (총 {len(final_good_for_jsonl)}개 데이터)\r\n")

    # Bad 데이터를 JSONL 파일로 1000개씩 추가 모드로 저장
    if not bad_data_cleaned.empty:
        print(f"[INFO] 최종 배드 데이터를 {output_bad_jsonl} 파일로 1000개씩 저장 중 (label 컬럼 제외)...\r\n")
        final_bad_for_jsonl = bad_data_cleaned.copy()
        save_dataframe_to_jsonl_in_chunks(final_bad_for_jsonl, output_bad_jsonl, chunk_size=1000)
        print(f"[INFO] JSONL 저장 완료: {output_bad_jsonl} (총 {len(final_bad_for_jsonl)}개 데이터)\r\n")
    else:
        print(f"[WARN] 저장할 배드 데이터가 없어 {output_bad_jsonl} 파일을 생성하지 않습니다.\r\n")

    print("\n--- 파이프라인 처리 완료 ---\n")
    
    # 파이프라인의 최종 결과 DataFrame들을 반환
    return final_good_data, iso_removed_data, lof_removed_data