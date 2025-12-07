from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import joblib
import os
import boto3
from dotenv import load_dotenv

# ==========================================
# 0. 앱 초기화
# ==========================================
app = FastAPI()

# 리액트(localhost:3000) 연결 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. 설정 및 데이터 로드
# ==========================================

# 전역 변수 초기화
df = pd.DataFrame()
model = None

# [대체 코드] 로컬 CSV 파일 로드
try:
    df = pd.read_csv('data.csv')

    bins = [0, 20, 30, 40, 50, 60, 100]
    labels = ['10대 이하', '20대', '30대', '40대', '50대', '60대 이상']

    df['age_group'] = pd.cut(df['age'], bins=bins, labels=labels, right=False)

    # 모델 로드 (파일이 있다면)
    try:
        model = joblib.load('studycafe_model_light.pkl')
        print("✅ 모델 로드 성공")
    except:
        print("⚠️ 모델 파일 없음 (예측 기능 불가)")

    print(f"✅ data.csv 로드 성공: {len(df)}건")
except Exception as e:
    print(f"❌ data.csv 로드 실패: {e}")


# ==========================================
# 2. API 구현
# ==========================================

# [API 0] 🗺️ 지도 시각화용 데이터
@app.get("/visualize")
def get_visualize_data():
    if df.empty: return []
    return df.to_dict(orient="records")

# [API 1] 🗺️ 지도 시각화용: 지역별 이용자 수 반환
@app.get("/map/users")
def get_map_users():
    if df.empty: return {}
    user_counts = df['region_city_group'].value_counts().to_dict()
    return user_counts

# =================================================================
# [수정된 부분] [API 2] 🤖 매출 예측 (리액트 연동용)
# =================================================================
class PredictInput(BaseModel):
    region: str         # 프론트에서 'region' ("Seoul")으로 보냄
    age: float          # 프론트에서 'age' (숫자)로 보냄
    visit_days: float   # 프론트에서 'visit_days' (숫자)로 보냄
    duration: float     # 프론트에서 'duration' (숫자)로 보냄

@app.post("/predict")
def predict(data: PredictInput):
    if model is None:
        raise HTTPException(status_code=500, detail="모델이 로드되지 않았습니다.")

    try:
        # 프론트엔드 데이터를 모델이 아는 컬럼명으로 매핑하여 DataFrame 생성
        input_df = pd.DataFrame([{
            'region_city_group': data.region,      # 모델 컬럼명: region_city_group
            'age': data.age,                       # 모델 컬럼명: age
            'visit_days': data.visit_days,         # 모델 컬럼명: visit_days
            'total_duration_min': data.duration    # 모델 컬럼명: total_duration_min
        }])

        # 예측 실행
        prediction = model.predict(input_df)[0]

        # 결과 반환
        return {"prediction": int(prediction)}

    except Exception as e:
        print(f"예측 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# =================================================================

# [API 3] 📊 다목적 차트 데이터
@app.get("/chart/dynamic")
def get_dynamic_chart(
    x_axis: str = Query(..., description="X축"),
    y_axis: str = Query(..., description="Y축")
):
    if df.empty: return []
    if x_axis not in df.columns:
        raise HTTPException(status_code=400, detail="Invalid X axis")

    grouped = df.groupby(x_axis)
    result = {}

    if y_axis == "users":
        result = grouped.size()
    elif y_axis == "sales":
        result = grouped['total_payment_may'].sum()
    elif y_axis == "retention":
        result = grouped['retained_90'].mean() * 100
    else:
        raise HTTPException(status_code=400, detail="Invalid Y axis")

    chart_data = []
    for key, value in result.items():
        chart_data.append({
            "label": str(key),
            "value": round(value, 2)
        })
    return chart_data

# [API 4] 💰 연령대별 매출 비율
@app.get("/chart/age-sales-ratio")
def get_age_sales_ratio():
    if df.empty: return []
    if 'age_group' not in df.columns: return []

    age_sales = df.groupby('age_group')['total_payment_may'].sum()
    total_revenue = age_sales.sum()

    result_data = []
    for age, sales in age_sales.items():
        if total_revenue == 0: ratio = 0
        else: ratio = (sales / total_revenue) * 100

        result_data.append({
            "age_group": str(age),
            "total_sales": int(sales),
            "ratio": round(ratio, 1)
        })
    return result_data