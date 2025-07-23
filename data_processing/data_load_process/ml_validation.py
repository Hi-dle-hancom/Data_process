# ml_validation.py (수정 제안)

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

def isolation_filter(df: pd.DataFrame) -> pd.DataFrame:
    # 이상치 탐지에 사용할 컬럼 리스트
    features = ['content_length', "cyclomatic_complexity", "maintainability_index", "comment_ratio"]

    # 모든 특성 컬럼이 DataFrame에 있는지 확인
    for col in features:
        if col not in df.columns:
            print(f"[WARN] IsolationForest: '{col}' 컬럼이 없어 필터링에 포함하지 않습니다.")
            # 없으면 해당 특성 제외 (또는 에러 발생)
            features.remove(col)

    if not features: # 사용할 특성이 없으면 필터링 스킵
        print("[WARN] IsolationForest: 유효한 특성 컬럼이 없어 필터링을 건너뜀.")
        return df.copy()

    iso = IsolationForest(contamination=0.1, random_state=42) # contamination 비율 조정 가능
    df_copy = df.copy() # 원본 DataFrame 변경 방지
    df_copy["anomaly_iso"] = iso.fit_predict(df_copy[features])
    filtered = df_copy[df_copy["anomaly_iso"] == 1].drop(columns=["anomaly_iso"]).reset_index(drop=True)
    print(f"[INFO] IsolationForest 이후 데이터 개수: {len(filtered)}")
    return filtered


def lof_filter(df: pd.DataFrame, n_neighbors: int = 20) -> pd.DataFrame:
    # 이상치 탐지에 사용할 컬럼 리스트
    features = ["content_length", "cyclomatic_complexity", "maintainability_index", "comment_ratio"]

    # 모든 특성 컬럼이 DataFrame에 있는지 확인
    for col in features:
        if col not in df.columns:
            print(f"[WARN] LOF: '{col}' 컬럼이 없어 필터링에 포함하지 않습니다.")
            features.remove(col)

    if not features: # 사용할 특성이 없으면 필터링 스킵
        print("[WARN] LOF: 유효한 특성 컬럼이 없어 필터링을 건너뜀.")
        return df.copy()

    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=0.1) # n_neighbors, contamination 조정 가능
    df_copy = df.copy() # 원본 DataFrame 변경 방지
    preds = lof.fit_predict(df_copy[features])
    df_copy["anomaly_lof"] = preds
    filtered = df_copy[df_copy["anomaly_lof"] == 1].drop(columns=["anomaly_lof"]).reset_index(drop=True)
    print(f"[INFO] LOF 이후 데이터 개수: {len(filtered)}")
    return filtered