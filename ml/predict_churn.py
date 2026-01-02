import pandas as pd
import mlflow
import mlflow.sklearn
import os
from sqlalchemy import create_engine, text

# Database Connection
db_user = os.getenv('POSTGRES_USER', 'user')
db_pass = os.getenv('POSTGRES_PASSWORD', 'password')
db_host = os.getenv('POSTGRES_HOST', 'postgres')
db_port = os.getenv('POSTGRES_PORT', '5432')
db_name = os.getenv('POSTGRES_DB', 'ecom')

connection_str = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
engine = create_engine(connection_str)

def predict_churn():
    print("Loading inference data from mart_churn_inference...")
    df = pd.read_sql("SELECT * FROM public_marts.mart_churn_inference", engine)
    
    # Feature Selection (Must match Training!)
    features = ['recency_days', 'frequency', 'monetary', 'avg_order_value', 'tenure_days']
    X = df[features]
    
    print(f"Data Shape: {X.shape}")
    
    # Load Latest Model from MLflow
    print("Loading latest model from MLflow...")
    experiment_name = "churn_prediction"
    current_experiment = mlflow.get_experiment_by_name(experiment_name)
    
    if current_experiment is None:
        print("Experiment not found!")
        return

    runs = mlflow.search_runs(experiment_ids=[current_experiment.experiment_id], 
                            order_by=["start_time DESC"], 
                            max_results=1)
    
    if runs.empty:
        print("No runs found!")
        return
        
    latest_run_id = runs.iloc[0]["run_id"]
    model_uri = f"runs:/{latest_run_id}/model"
    print(f"Using Model from Run ID: {latest_run_id}")
    
    model = mlflow.sklearn.load_model(model_uri)
    
    # Predict
    print("Scoring users...")
    y_prob = model.predict_proba(X)[:, 1]
    
    # Create Results DataFrame
    results = pd.DataFrame({
        'user_id': df['user_id'],
        'churn_probability': y_prob,
        'prediction_ts': pd.Timestamp.now()
    })
    
    # Write to Postgres
    print("Writing predictions to analytics.churn_predictions...")
    # Create schema if not exists
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS analytics;"))
        conn.commit()
    
    results.to_sql('churn_predictions', engine, schema='analytics', if_exists='replace', index=False)
    print("Inference Complete. Predictions saved.")

if __name__ == "__main__":
    predict_churn()
