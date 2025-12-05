from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import joblib
import os
import boto3
from dotenv import load_dotenv # 👈 새로 추가!

# ==========================================
# 1. 설정 및 데이터 로드 (AWS DynamoDB 연결)
# ==========================================

# 1-1. 환경 변수 로드 (이 코드가 .env 파일을 읽어옴)
load_dotenv() 

# 1-2. .env 파일에서 정보 가져오기 (가장 중요한 부분)
ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
REGION = os.getenv("AWS_REGION")
TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME")

# 1-3. AWS DynamoDB 연결
try:
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=REGION, 
        aws_access_key_id=ACCESS_KEY,  
        aws_secret_access_key=SECRET_KEY
    )
    table = dynamodb.Table(TABLE_NAME)
    print(f"✅ DB 테이블 연결 성공: {TABLE_NAME}")
    
    # DB 전체 스캔 및 데이터프레임 변환 로직은 그대로 유지
    response = table.scan()
    items = response['Items']
    
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
        
    df = pd.DataFrame(items)
    
    # 숫자 컬럼 변환 로직
    numeric_cols = ['age', 'visit_days', 'total_duration_min', 'total_payment_may', 'retained_90']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    print(f"✅ DB 데이터 로드 완료: {len(df)}건")

except Exception as e:
    print(f"❌ DB 연결/로드 실패: {e}")
    # 키가 잘못되었거나 테이블 이름이 틀리면 여기서 에러가 납니다.
    df = pd.DataFrame() 
    # 에러가 나더라도 서버는 켜져야 하므로 FastAPI의 HTTPException은 여기서 사용하지 않습니다.

# (나머지 Prediction Model Load, FastAPI 정의, API 함수들은 그대로 유지합니다.)
# ...
