import optuna
import mlflow
import mlflow.xgboost
import pandas as pd
import numpy as np
import xgboost as xgb
from sqlalchemy import create_engine
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import average_precision_score, precision_score, recall_score, roc_auc_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
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

def objective(trial):
    df = load_data()
    
    # Features
    numeric_features = ['recency_days', 'frequency_60d', 'frequency_30d', 'tenure_days', 
                       'total_events', 'view_count', 'cart_count', 'session_count', 'view_to_cart_rate', 'frequency_all_time']
    categorical_features = ['traffic_source', 'country', 'gender']
    target = 'is_churned'

    # Preprocessing (Manual OHE for XGBoost)
    df_encoded = pd.get_dummies(df, columns=categorical_features, drop_first=True)
    
    # Align columns
    feature_cols = [c for c in df_encoded.columns if c not in ['user_id', 'snapshot_date', target] and c in numeric_features + list(df_encoded.columns)]
    
    X = df_encoded[feature_cols]
    y = df_encoded[target]
    
    # Search Space
    param = {
        'objective': 'binary:logistic',
        'eval_metric': 'aucpr',
        'booster': 'gbtree',
        'lambda': trial.suggest_float('lambda', 1e-8, 1.0, log=True),
        'alpha': trial.suggest_float('alpha', 1e-8, 1.0, log=True),
        'max_depth': trial.suggest_int('max_depth', 1, 9),
        'eta': trial.suggest_float('eta', 1e-8, 1.0, log=True),
        'gamma': trial.suggest_float('gamma', 1e-8, 1.0, log=True),
        'grow_policy': trial.suggest_categorical('grow_policy', ['depthwise', 'lossguide']),
        'scale_pos_weight': trial.suggest_float('scale_pos_weight', 1, 10), # Handle imbalance
    }

    # Cross Validation (Stratified 3-Fold)
    skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    scores = []
    
    for train_index, valid_index in skf.split(X, y):
        X_train, X_valid = X.iloc[train_index], X.iloc[valid_index]
        y_train, y_valid = y.iloc[train_index], y.iloc[valid_index]
        
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dvalid = xgb.DMatrix(X_valid, label=y_valid)
        
        # Train
        bst = xgb.train(param, dtrain)
        preds = bst.predict(dvalid)
        
        # Metric: Average Precision (Good for imbalance)
        score = average_precision_score(y_valid, preds)
        scores.append(score)
        
    return np.mean(scores)

def tune_model():
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
    mlflow.set_experiment("churn_hyperopt")
    
    with mlflow.start_run(run_name="Optuna_Optimization"):
        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=20) # 20 trials for speed
        
        print(f"Number of finished trials: {len(study.trials)}")
        print("Best trial:")
        trial = study.best_trial
        
        print(f"  Value: {trial.value}")
        print("  Params: ")
        for key, value in trial.params.items():
            print(f"    {key}: {value}")
            mlflow.log_param(key, value)
            
        mlflow.log_metric("best_avg_precision", trial.value)
        
        # Save best params to file
        with open("ml/best_params.txt", "w") as f:
            f.write(str(trial.params))

if __name__ == "__main__":
    tune_model()
