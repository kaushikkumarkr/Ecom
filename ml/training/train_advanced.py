import pandas as pd
import numpy as np
import mlflow
import mlflow.xgboost
import xgboost as xgb
import shap
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, confusion_matrix, average_precision_score
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Database Connection
db_user = os.getenv('POSTGRES_USER', 'user')
db_pass = os.getenv('POSTGRES_PASSWORD', 'password')
db_host = os.getenv('POSTGRES_HOST', 'postgres')
db_port = os.getenv('POSTGRES_PORT', '5432')
db_name = os.getenv('POSTGRES_DB', 'ecom')

connection_str = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
engine = create_engine(connection_str)

def load_data():
    print("Loading Features and Labels from Postgres...")
    query = """
    SELECT 
        f.*,
        l.is_churned
    FROM public_marts.churn_features f
    JOIN public_marts.churn_labels l ON f.user_id = l.user_id
    """
    df = pd.read_sql(query, engine)
    return df

def train_advanced():
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5001"))
    mlflow.set_experiment("churn_prediction_project2")
    
    with mlflow.start_run(run_name="Advanced_XGBoost"):
        df = load_data()
        
        # Features
        numeric_features = ['recency_days', 'frequency_60d', 'frequency_30d', 'tenure_days', 
                           'total_events', 'view_count', 'cart_count', 'session_count', 'view_to_cart_rate', 'frequency_all_time']
        categorical_features = ['traffic_source', 'country', 'gender']
        target = 'is_churned'
        
        # Preprocessing (Minimal since XGBoost handles nulls, but we need encoding)
        X = df[numeric_features + categorical_features].copy()
        y = df[target]
        
        # One-Hot Encoding
        X = pd.get_dummies(X, columns=categorical_features, drop_first=True)
        
        # Train/Test Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # Calculate Scale Pos Weight (Imbalance)
        neg_count = (y_train == 0).sum()
        pos_count = (y_train == 1).sum()
        scale_pos_weight = neg_count / pos_count
        
        # XGBoost Model (Tuned via Optuna - Sprint 6)
        params = {
            "objective": "binary:logistic",
            "eval_metric": "auc",
            "max_depth": 9,
            "learning_rate": 0.82, 
            "n_estimators": 200,
            "scale_pos_weight": 1.008,
            "gamma": 0.0056,
            "reg_alpha": 1.08e-06,
            "reg_lambda": 1.52e-05,
            "grow_policy": 'depthwise',
            "random_state": 42
        }
        
        mlflow.log_params(params)
        
        model = xgb.XGBClassifier(**params)
        
        print("Training XGBoost...")
        model.fit(X_train, y_train)
        
        # Evaluate
        print("Evaluating...")
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        auc = roc_auc_score(y_test, y_prob)
        f1 = f1_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        
        print(f"AUC: {auc:.4f}")
        print(f"F1: {f1:.4f}")
        
        mlflow.log_metric("auc", auc)
        mlflow.log_metric("f1_score", f1)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)
        
        # Additional Metric: Average Precision (Optimized in Tune)
        avg_precision = average_precision_score(y_test, y_prob)
        print(f"Average Precision (AUPRC): {avg_precision:.4f}")
        mlflow.log_metric("average_precision", avg_precision)
        
        # Feature Importance (SHAP)
        print("Generating SHAP Explanations...")
        explainer = shap.Explainer(model)
        shap_values = explainer(X_test)
        
        # Summary Plot
        plt.figure(figsize=(10, 8))
        shap.summary_plot(shap_values, X_test, show=False)
        plt.tight_layout()
        plt.savefig("shap_summary.png")
        mlflow.log_artifact("shap_summary.png")
        os.remove("shap_summary.png")
        
        # Register Model
        # Register Model (Log Booster to avoid sklearn wrapper issues)
        booster = model.get_booster()
        mlflow.xgboost.log_model(booster, "model", registered_model_name="churn_prediction_advanced")
        print("Model Registered in MLflow.")

if __name__ == "__main__":
    train_advanced()
