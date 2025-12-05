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

# ==========================================
# 2. API 구현 (확정된 4가지 기능)
# ==========================================

# [API 1] 🗺️ 지도 시각화용: 지역별 이용자 수 반환
@app.get("/map/users")
def get_map_users():
    """
    지도에 원을 그리기 위해 지역별 이용자 수를 반환합니다.
    반환 예시: {"Seoul": 150, "Gyeonggi-do": 300, ...}
    """
    if df.empty: return {}
    
    # 지역(region_city_group)별 개수 세기
    user_counts = df['region_city_group'].value_counts().to_dict()
    return user_counts


# [API 2] 🤖 매출 예측: 입력값을 받아 예상 매출 반환
class PredictionRequest(BaseModel):
    region_city_group: str
    age: int
    visit_days: int
    total_duration_min: int

@app.post("/predict/sales")
def predict_sales(data: PredictionRequest):
    """
    사용자 정보를 입력받아 예상 월 매출을 예측합니다.
    """
    if model is None:
        raise HTTPException(status_code=500, detail="모델이 로드되지 않았습니다.")
    
    try:
        # 모델 입력용 데이터프레임 생성
        input_df = pd.DataFrame([data.dict()])
        
        # 예측 수행
        prediction = model.predict(input_df)[0]
        return {"predicted_payment": int(prediction)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# [API 3] 📊 다목적 차트 데이터: X축(조건)과 Y축(목표값)을 받아 통계 반환
@app.get("/chart/dynamic")
def get_dynamic_chart(
    x_axis: str = Query(..., description="X축 기준: region_city_group 또는 age_group"),
    y_axis: str = Query(..., description="Y축 값: users(수), sales(매출), retention(재방문율)")
):
    """
    드롭다운 선택에 따라 동적으로 차트 데이터를 생성합니다.
    예: /chart/dynamic?x_axis=age_group&y_axis=sales (연령대별 매출)
    """
    if df.empty: return []

    # 1. 그룹화(Grouping)
    if x_axis not in ['region_city_group', 'age_group']:
        raise HTTPException(status_code=400, detail="X축은 지역(region_city_group) 또는 연령대(age_group)만 가능합니다.")

    grouped = df.groupby(x_axis)

    # 2. 집계(Aggregation) 로직 분기
    result = {}
    
    if y_axis == "users":
        # 이용자 수 (Count)
        result = grouped.size()
        
    elif y_axis == "sales":
        # 총 매출액 (Sum)
        result = grouped['total_payment_may'].sum()
        
    elif y_axis == "retention":
        # 재방문률 (Mean) - retained_90 컬럼의 평균 * 100
        result = grouped['retained_90'].mean() * 100
        
    else:
        raise HTTPException(status_code=400, detail="Y축은 users, sales, retention 중 하나여야 합니다.")

    # 3. 프론트엔드 차트 라이브러리가 좋아하는 형식으로 변환 (List of Objects)
    # 예: [{"label": "Seoul", "value": 150}, ...]
    chart_data = []
    for key, value in result.items():
        chart_data.append({
            "label": key,
            "value": round(value, 2)  # 소수점 2자리 반올림
        })
    
    return chart_data


# [API 4] 💰 연령대별 매출 비율: 매출액과 전체 대비 비율(%) 반환
@app.get("/chart/age-sales-ratio")
def get_age_sales_ratio():
    """
    연령대별 총 매출과 전체 매출 대비 비율을 계산합니다.
    """
    if df.empty: return []

    # 연령대별 매출 합계 계산
    age_sales = df.groupby('age_group')['total_payment_may'].sum()
    
    # 전체 총 매출
    total_revenue = age_sales.sum()

    result_data = []
    for age, sales in age_sales.items():
        ratio = (sales / total_revenue) * 100
        result_data.append({
            "age_group": age,
            "total_sales": int(sales),
            "ratio": round(ratio, 1)  # 비율은 소수점 1자리
        })
    
    return result_data
