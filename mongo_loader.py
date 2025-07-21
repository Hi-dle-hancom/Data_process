# mongo_loader.py

import pandas as pd
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, InvalidURI

# MongoDB에서 데이터 로딩
def load_data_from_mongo(uri: str, db: str, collection: str, query=None, limit: int = 0) -> pd.DataFrame: # <-- limit 인자 추가
    try:
        client = MongoClient(uri)
        coll = client[db][collection]
        
        # limit 적용 부분
        if limit > 0:
            data = list(coll.find(query or {}).limit(limit))
        else:
            data = list(coll.find(query or {}))

        if not data:
            print(f"[WARN] MongoDB '{db}.{collection}'에서 데이터 없음")
            return pd.DataFrame()
        df = pd.DataFrame(data)
        if "_id" in df.columns:
            df = df.drop(columns=["_id"])
        print(f"[INFO] MongoDB '{db}.{collection}'에서 {len(df)}개 데이터 로드 완료 (제한: {limit if limit > 0 else '없음'}).") # 로그 메시지 수정
        return df
    except InvalidURI as e:
        print(f"[ERROR] MongoDB URI가 잘못되었습니다: {e}")
        return pd.DataFrame()
    except ConnectionFailure as e:
        print(f"[ERROR] MongoDB 연결 실패: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"[ERROR] 데이터 로딩 중 예상치 못한 오류 발생: {e}")
        return pd.DataFrame()

# DataFrame을 MongoDB에 저장하는 함수
def save_data_to_mongo(df: pd.DataFrame, uri: str, db: str, collection: str):
    if df.empty:
        print(f"[INFO] 저장할 데이터가 없습니다. 컬렉션 '{collection}'에 데이터 저장 스킵.")
        return

    try:
        client = MongoClient(uri)
        coll = client[db][collection]

        # 기존 데이터 삭제 (선택 사항: 덮어쓰려면 이 줄 사용)
        # coll.delete_many({}) # 경고: 이 줄을 사용하면 기존 데이터가 모두 삭제됩니다.

        # _id 컬럼이 있다면 제거 (MongoDB가 _id를 자동 생성하도록)
        if "_id" in df.columns:
            df_to_save = df.drop(columns=["_id"])
        else:
            df_to_save = df.copy() # 원본 DataFrame 변경 방지

        # NaN 값을 None으로 변환 (MongoDB는 NaN을 지원하지 않음)
        df_to_save = df_to_save.where(pd.notna(df_to_save), None)

        # DataFrame을 딕셔너리 리스트로 변환
        data_dict = df_to_save.to_dict(orient="records")

        if data_dict: # 데이터가 실제로 존재할 때만 insert
            coll.insert_many(data_dict)
            print(f"[INFO] {len(data_dict)}개 데이터가 MongoDB '{db}.{collection}'에 저장 완료.")
        else:
            print(f"[WARN] 변환된 데이터가 없어 컬렉션 '{collection}'에 저장할 내용이 없습니다.")

    except InvalidURI as e:
        print(f"[ERROR] MongoDB URI가 잘못되었습니다: {e}")
    except ConnectionFailure as e:
        print(f"[ERROR] MongoDB 연결 실패: {e}")
    except Exception as e:
        print(f"[ERROR] 데이터 저장 중 예상치 못한 오류 발생: {e}")