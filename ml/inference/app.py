from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mlflow.xgboost
import pandas as pd
from sqlalchemy import create_engine, text
import os
import numpy as np

# Database Connection
db_user = os.getenv('POSTGRES_USER', 'user')
db_pass = os.getenv('POSTGRES_PASSWORD', 'password')
db_host = os.getenv('POSTGRES_HOST', 'postgres')
db_port = os.getenv('POSTGRES_PORT', '5432')
db_name = os.getenv('POSTGRES_DB', 'ecom')

connection_str = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
engine = create_engine(connection_str)

# MLflow Config
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5001"))
model_name = "churn_prediction_advanced"
model = None

# App Definition
app = FastAPI(title="Churn Prediction API", version="1.0")

class PredictionRequest(BaseModel):
    user_id: int

class PredictionResponse(BaseModel):
    user_id: int
    churn_probability: float
    is_high_risk: bool
    recommended_action: str

@app.on_event("startup")
def load_model():
    global model
    try:
        print(f"Loading Model: {model_name}...")
        # In production, use "models:/{model_name}/Production". Here we use "latest" or specific run.
        # Since we just registered it, let's grab the latest version.
        client = mlflow.MlflowClient()
        latest_version = client.get_latest_versions(model_name, stages=["None"])[0].version
        model_uri = f"models:/{model_name}/{latest_version}"
        model = mlflow.xgboost.load_model(model_uri)
        print("Model Loaded Successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")

def get_user_features(user_id: int):
    # Fetch features from the "Inference Feature Mart" (churn_scoring)
    query = text("SELECT * FROM public_marts.churn_scoring WHERE user_id = :user_id")
    with engine.connect() as conn:
        result = conn.execute(query, {"user_id": user_id}).fetchone()
    
    if not result:
        return None
        
    # Convert to DataFrame to match training format
    # Columns must verify against SQL schema
    cols = result._mapping.keys()
    vals = result._mapping.values()
    df = pd.DataFrame([vals], columns=cols)
    return df

def align_features(df_inference):
    # Same logic as batch_score.py (DRY violation but simple for now)
    numeric_features = ['recency_days', 'frequency_60d', 'frequency_30d', 'tenure_days', 
                       'total_events', 'view_count', 'cart_count', 'session_count', 'view_to_cart_rate', 'frequency_all_time']
    categorical_features = ['traffic_source', 'country', 'gender']
    
    # Encode with pandas get_dummies
    # Issue: Single row might miss categories. 
    # Fix: We really should use a pre-fitted encoder pipeline.
    # Hack for Project 2: Force dummy columns.
    
    if model is None:
        raise ValueError("Model not loaded")

    df_encoded = pd.get_dummies(df_inference[numeric_features + categorical_features], 
                                columns=categorical_features, 
                                drop_first=True)
    
    # Align cols
    booster = model.get_booster()
    model_features = booster.feature_names
    
    for feat in model_features:
        if feat not in df_encoded.columns:
            df_encoded[feat] = 0
            
    return df_encoded[model_features]

@app.post("/predict", response_model=PredictionResponse)
def predict_churn(request: PredictionRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not initialized")
        
    df = get_user_features(request.user_id)
    if df is None:
        raise HTTPException(status_code=404, detail="User not found in scoring mart")
        
    # Preprocess
    try:
        X = align_features(df)
        
        # Predict
        prob = float(model.predict_proba(X)[:, 1][0])
        
        # Action Logic
        # Action Logic: >0.7 = High Risk
        action = "Retain" if prob < 0.5 else "Send Coupon"
        if prob > 0.8:
            action = "Call Customer"
            
        return {
            "user_id": request.user_id,
            "churn_probability": prob,
            "is_high_risk": prob > 0.7,
            "recommended_action": action
        }
    except Exception as e:
        print(f"Prediction Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy", "model_loaded": model is not None}
