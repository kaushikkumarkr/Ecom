import pandas as pd
import numpy as np
import mlflow
import mlflow.xgboost
from sqlalchemy import create_engine, text
import os

# Database Connection
db_user = os.getenv('POSTGRES_USER', 'user')
db_pass = os.getenv('POSTGRES_PASSWORD', 'password')
db_host = os.getenv('POSTGRES_HOST', 'postgres')
db_port = os.getenv('POSTGRES_PORT', '5432')
db_name = os.getenv('POSTGRES_DB', 'ecom')

connection_str = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
engine = create_engine(connection_str)

def get_inference_data():
    print("Loading Inference Data (Today's Active Users)...")
    query = "SELECT * FROM public_marts.churn_scoring"
    df = pd.read_sql(query, engine)
    print(f"Users to Score: {len(df)}")
    return df

def align_features(df_inference):
    # Features used in training (Must match train_advanced.py)
    numeric_features = ['recency_days', 'frequency_60d', 'frequency_30d', 'tenure_days', 
                       'total_events', 'view_count', 'cart_count', 'session_count', 'view_to_cart_rate', 'frequency_all_time']
    categorical_features = ['traffic_source', 'country', 'gender']
    
    # Encode
    df_encoded = pd.get_dummies(df_inference[numeric_features + categorical_features], 
                                columns=categorical_features, 
                                drop_first=True)
    
    # We must match the model's expected columns. 
    # In a real system, we'd load the feature list from an artifact.
    # Here, we'll ensure common dummy columns exist.
    # (Simplified: relying on XGBoost to handle missing cols if we named them right, 
    # but strictly we should add missing cols as 0).
    
    return df_encoded

def batch_score():
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5001"))
    
    # Load Model (Latest Version of Advanced)
    model_name = "churn_prediction_advanced"
    print(f"Loading Model: {model_name}...")
    model = mlflow.xgboost.load_model(f"models:/{model_name}/latest")
    
    # Load Data
    df = get_inference_data()
    X = align_features(df)
    
    # Align Columns (XGBoost is picky about column order matches sometimes, or just names)
    # We will try predicting. If it fails due to mismatch, we'd add missing cols here.
    # For robust handling, we get booster feature names:
    booster = model.get_booster()
    model_features = booster.feature_names
    
    # Add missing columns with 0
    for feat in model_features:
        if feat not in X.columns:
            X[feat] = 0
            
    # Reorder to match model
    X = X[model_features]
    
    # Predict
    print("Scoring Users...")
    probs = model.predict_proba(X)[:, 1]
    df['churn_probability'] = probs
    
    # --- Actionability Logic ---
    # Assumptions
    LTV = 150.0  # Avg Lifetime Value in $
    WINBACK_RATE = 0.30 # Success rate of coupon
    COST = 10.0 # Cost of intervention
    
    # Expected Value = (Value Saved) - Cost
    # Value Saved = Probability of Churn * LTV * Winback Probability
    df['expected_uplift_value'] = (df['churn_probability'] * LTV * WINBACK_RATE) - COST
    
    # Recommended Action
    conditions = [
        (df['expected_uplift_value'] > 20) & (df['churn_probability'] > 0.7), # High Value & High Risk
        (df['expected_uplift_value'] > 0), # Positive ROI
    ]
    choices = ['High Priority Call', 'Send Email Coupon']
    df['recommended_action'] = np.select(conditions, choices, default='No Action')
    
    # Prepare Output
    output = df[['user_id', 'scoring_date', 'churn_probability', 'expected_uplift_value', 'recommended_action', 'traffic_source']]
    
    # Write to DB
    print("Writing to analytics.churn_scores...")
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS analytics"))
        conn.commit()
        
    output.to_sql('churn_scores', engine, schema='analytics', if_exists='replace', index=False)
    
    # Create Retention Targets View (Top 100)
    top_targets = output[output['recommended_action'] != 'No Action'].sort_values('expected_uplift_value', ascending=False).head(500)
    top_targets.to_sql('retention_targets', engine, schema='analytics', if_exists='replace', index=False)
    
    print(f"Success! Scored {len(df)} users. Top 500 targets saved.")

if __name__ == "__main__":
    batch_score()
