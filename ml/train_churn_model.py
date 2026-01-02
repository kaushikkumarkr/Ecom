import pandas as pd
import xgboost as xgb
import mlflow
import mlflow.xgboost
import shap
import matplotlib.pyplot as plt
import os
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score, confusion_matrix
from imblearn.over_sampling import SMOTE

# Database Connection
db_user = os.getenv('POSTGRES_USER', 'user')
db_pass = os.getenv('POSTGRES_PASSWORD', 'password')
db_host = os.getenv('POSTGRES_HOST', 'postgres')
db_port = os.getenv('POSTGRES_PORT', '5432')
db_name = os.getenv('POSTGRES_DB', 'ecom')

connection_str = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
engine = create_engine(connection_str)

def train_model():
    print("Loading data from mart_churn_features...")
    df = pd.read_sql("SELECT * FROM public_marts.mart_churn_features", engine)
    
    # Feature Selection
    features = ['recency_days', 'frequency', 'monetary', 'avg_order_value', 'tenure_days']
    target = 'is_churned'
    
    X = df[features]
    y = df[target]
    
    print(f"Data Shape: {X.shape}")
    print(f"Class Balance: \n{y.value_counts()}")
    
    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Handle Imbalance (SMOTE)
    print("Applying SMOTE to handle class imbalance...")
    smote = SMOTE(random_state=42)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
    
    # MLflow Experiment
    mlflow.set_experiment("churn_prediction")
    
    with mlflow.start_run():
        print("Training XGBoost Classifier...")
        # Hyperparameters
        params = {
            "n_estimators": 100,
            "max_depth": 4,
            "learning_rate": 0.1,
            "objective": "binary:logistic",
            "random_state": 42
        }
        
        mlflow.log_params(params)
        
        model = xgb.XGBClassifier(**params)
        model.fit(X_train_resampled, y_train_resampled)
        
        # Predictions
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        # Metrics
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_prob)
        
        print(f"Accuracy: {acc:.4f}")
        print(f"Precision: {prec:.4f}")
        print(f"Recall: {rec:.4f}")
        print(f"AUC: {auc:.4f}")
        
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("precision", prec)
        mlflow.log_metric("recall", rec)
        mlflow.log_metric("auc", auc)
        
        # Log Model (Use sklearn flavor for Wrapper)
        mlflow.sklearn.log_model(model, "model")
        
        # Explainability (SHAP)
        print("Generating SHAP plots...")
        explainer = shap.Explainer(model)
        shap_values = explainer(X_test)
        
        # Summary Plot
        plt.figure()
        shap.summary_plot(shap_values, X_test, show=False)
        plt.savefig("shap_summary.png", bbox_inches='tight')
        mlflow.log_artifact("shap_summary.png")
        plt.close()
        
        print("Training Complete. Model logged to MLflow.")

if __name__ == "__main__":
    train_model()
