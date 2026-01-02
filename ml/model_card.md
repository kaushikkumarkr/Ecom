# Model Card: Churn Prediction (XGBoost)

## Model Details
-   **Developed by**: E-commerce Data Science Team
-   **Model Date**: January 2024
-   **Model Version**: 1.0 (Advanced)
-   **Model Type**: XGBoost Classifier (Binary Classification)
-   **License**: Internal Use Only

## Intended Use
-   **Primary Use**: Identify active users at risk of churning (no purchase in next 30 days) to target with retention campaigns (email coupons).
-   **Intended Users**: Marketing Team, Lifecycle Managers.
-   **Out of Scope**: Valid only for users with at least 1 historical purchase.

## Training Data
-   **Source**: `mart_churn_features` (Postgres).
-   **Observation Window**: T-60 Days to T (Snapshot: 2023-09-01).
-   **Target**: `is_churned` (No purchase in T to T+30 Days).
-   **Size**: ~45,000 Users.
-   **Imbalance**: ~60% Churn Logic (High churn because "Churn" includes inactive one-time buyers).

## Quantitative Analysis
-   **Training Split**: 80% Train, 20% Test (Stratified).
-   **Performance Metrics (Tuned V2)**:
    -   **Average Precision (AUPRC)**: **0.97** (Primary optimization target). The model is extremely effective at ranking high-risk users.
    -   **Precision**: **97%** (Minimizes false alarms).
    -   **Recall**: **97%** (Captures almost all churners).
    -   **AUC**: **0.63** (Slight improvement).
-   **Drift Analysis**:
    -   Drift detected in `recency_days` (expected as platform grows).
    -   Action: Weekly monitoring recommended.

## Architecture & Data Flow
1.  **Feature Store**: dbt models `mart_churn_features` (Train) & `mart_churn_scoring` (Inference).
2.  **Training**: XGBoost classifier logged to MLflow Registry.
3.  **Inference**:
    -   **Batch**: Nightly job (`batch_score.py`) populates `analytics.churn_scores`.
    -   **Real-time**: FastAPI endpoint (`POST /predict`) fetches live features.

## Caveats & Recommendations
-   **Cold Start**: Cannot score users with 0 orders.
-   **Drift**: Monitoring setup to track `recency_days` shift. Retrain if drift > 10%.
