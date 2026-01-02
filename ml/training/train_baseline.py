import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, confusion_matrix
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
    print(f"Data Loaded: {df.shape}")
    return df

def train_baseline():
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5001"))
    mlflow.set_experiment("churn_prediction_project2")
    
    with mlflow.start_run(run_name="Baseline_LogReg"):
        df = load_data()
        
        # Features
        numeric_features = ['recency_days', 'frequency_60d', 'frequency_30d', 'tenure_days', 
                           'total_events', 'view_count', 'cart_count', 'session_count', 'view_to_cart_rate', 'frequency_all_time']
        categorical_features = ['traffic_source', 'country', 'gender']
        target = 'is_churned'
        
        X = df[numeric_features + categorical_features]
        y = df[target]
        
        # Train/Test Split (Simulating a holdout set)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # Preprocessing Pipeline
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])
        
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
            ('onehot', OneHotEncoder(handle_unknown='ignore'))
        ])
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, numeric_features),
                ('cat', categorical_transformer, categorical_features)
            ])
        
        # Model
        clf = Pipeline(steps=[('preprocessor', preprocessor),
                              ('classifier', LogisticRegression(max_iter=1000, class_weight='balanced'))])
        
        # Params
        params = {
            "model": "LogisticRegression",
            "class_weight": "balanced",
            "max_iter": 1000
        }
        mlflow.log_params(params)
        
        # Train
        print("Training Model...")
        clf.fit(X_train, y_train)
        
        # Evaluate
        print("Evaluating...")
        y_pred = clf.predict(X_test)
        y_prob = clf.predict_proba(X_test)[:, 1]
        
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
        
        # Confusion Matrix Plot
        cm = confusion_matrix(y_test, y_pred)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.title('Confusion Matrix')
        plt.ylabel('Actual')
        plt.xlabel('Predicted')
        plt.savefig("confusion_matrix.png")
        mlflow.log_artifact("confusion_matrix.png")
        os.remove("confusion_matrix.png")
        
        # Log Model
        mlflow.sklearn.log_model(clf, "model")
        print("Run Complete. Logged to MLflow.")

if __name__ == "__main__":
    train_baseline()
