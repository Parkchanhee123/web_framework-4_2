from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import joblib
import os

app = FastAPI()

# ==========================================
# 1. 설정 및 데이터 로드 (가짜 DB 역할)
# ==========================================

# CORS 설정 (프론트엔드 React와 통신 허용)
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터 파일 및 모델 경로
DATA_PATH = "data.csv"           # 데이터 파일 (DB 대용)
MODEL_PATH = "studycafe_model_light.pkl" # 예측 모델

# 서버 시작 시 데이터와 모델 미리 로드
if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH)
    print(f"✅ 데이터 로드 완료: {len(df)}건")
else:
    print("❌ 경고: data.csv가 없습니다. DB 연결 전까지는 작동하지 않습니다.")
    df = pd.DataFrame() # 빈 데이터프레임

if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
    print("✅ 예측 모델 로드 완료")
else:
    model = None
    print("❌ 경고: 모델 파일이 없습니다.")

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