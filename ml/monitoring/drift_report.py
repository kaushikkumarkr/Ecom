import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import os
import matplotlib.pyplot as plt
import seaborn as sns

# Database Connection
db_user = os.getenv('POSTGRES_USER', 'user')
db_pass = os.getenv('POSTGRES_PASSWORD', 'password')
db_host = os.getenv('POSTGRES_HOST', 'postgres')
db_port = os.getenv('POSTGRES_PORT', '5432')
db_name = os.getenv('POSTGRES_DB', 'ecom')

connection_str = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
engine = create_engine(connection_str)

def generate_drift_report():
    print("Generating Drift Report...")
    
    # 1. Load Reference Data (Training)
    print("Loading Training Data (Reference)...")
    train_df = pd.read_sql("SELECT * FROM public_marts.churn_features", engine)
    
    # 2. Load Current Data (Inference)
    print("Loading Inference Data (Current)...")
    score_df = pd.read_sql("SELECT * FROM public_marts.churn_scoring", engine)
    
    # 3. Compare Distributions
    report_path = "reports/drift_report.html"
    
    # Features to check
    features = ['recency_days', 'frequency_60d', 'total_events', 'view_count']
    
    # Create HTML
    html_content = "<html><head><title>Drift Report</title></head><body>"
    html_content += "<h1>Data Drift Report: Training vs Inference</h1>"
    html_content += f"<p>Training Rows: {len(train_df)} | Inference Rows: {len(score_df)}</p>"
    
    for feat in features:
        plt.figure(figsize=(10, 5))
        sns.kdeplot(train_df[feat], label='Training (Ref)', shade=True, color='blue')
        sns.kdeplot(score_df[feat], label='Inference (Curr)', shade=True, color='red')
        plt.title(f"Distribution: {feat}")
        plt.legend()
        
        img_path = f"reports/{feat}_drift.png"
        plt.savefig(img_path)
        plt.close()
        
        # Calculate Shift (Simple Mean difference)
        train_mean = train_df[feat].mean()
        curr_mean = score_df[feat].mean()
        drift_perc = ((curr_mean - train_mean) / train_mean) * 100
        
        html_content += f"<h2>Feature: {feat}</h2>"
        html_content += f"<p>Train Mean: {train_mean:.2f} | Current Mean: {curr_mean:.2f} | Shift: {drift_perc:.1f}%</p>"
        html_content += f"<img src='{feat}_drift.png' width='600'><br><hr>"
        
    html_content += "</body></html>"
    
    with open(report_path, "w") as f:
        f.write(html_content)
        
    print(f"Report saved to {report_path}")

if __name__ == "__main__":
    generate_drift_report()
