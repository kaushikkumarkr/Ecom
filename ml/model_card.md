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
-   **Performance Metrics**:
    -   **AUC**: 0.62 (Behavioral data noisy).
    -   **Precision**: 93% (High confidence in positive predictions).
    -   **Recall**: 67% (Captures 2/3rds of churners).

## Ethical Considerations
-   **Bias**: Model uses "Country" and "Gender" as features. Ensure coupons are not withheld from protected groups unfairly (fairness check recommended for V2).
-   **Privacy**: Uses only first-party behavioral data. No PII used in training.

## Caveats & Recommendations
-   **Cold Start**: Cannot score users with 0 orders.
-   **Drift**: Monitoring setup to track `recency_days` shift. Retrain if drift > 10%.
