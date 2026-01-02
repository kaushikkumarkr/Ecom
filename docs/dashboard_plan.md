# Metabase Dashboard Plan: Churn Risk & Retention

**Goal**: Enable marketing/success teams to target high-risk, high-value users.

## 1. Top Level Metrics (Key Indicators)
-   **Revenue at Risk**: Sum of `expected_uplift_value` for all high-risk users.
    ```sql
    SELECT sum(expected_uplift_value) 
    FROM analytics.churn_scores 
    WHERE recommended_action != 'No Action'
    ```
-   **High Risk User Count**: Count of users with `churn_probability > 0.7`.
-   **Average Churn Probability**: To track overall health trend.

## 2. Charts & Visualizations

### A. Churn Risk Distribution (Histogram)
-   **Question**: How is the risk distributed across our user base?
-   **Chart Type**: Bar Chart (Histogram bucketed by 0.1).
-   **SQL**:
    ```sql
    SELECT floor(churn_probability * 10) / 10 as risk_bucket, count(*) 
    FROM analytics.churn_scores
    GROUP BY 1 ORDER BY 1
    ```

### B. Risk by Traffic Source (Bar Chart)
-   **Question**: Which channels bring the riskiest users?
-   **Chart Type**: Bar Chart.
-   **SQL**:
    ```sql
    SELECT traffic_source, avg(churn_probability) as avg_risk 
    FROM analytics.churn_scores 
    GROUP BY 1 ORDER BY 2 DESC
    ```

### C. Retention Target List (Table)
-   **Question**: Who should I contact TODAY?
-   **Chart Type**: Table (Actionable List).
-   **Filters**: `Recommended Action != 'No Action'`.
-   **Columns**: `User ID`, `Email` (join raw.users), `Churn Prob`, `Exp. Uplift`, `Action`.
-   **Sorting**: `Expected Uplift` DESC.

## 3. Implementation Steps in Metabase
1.  **Sync Schema**: Go to Admin -> Databases -> Sync Database Schema Now (to see `analytics.churn_scores`).
2.  **Create Questions**: Use the SQL above or the Query Builder on the `churn_scores` table.
3.  **Assemble Dashboard**: Arrange metrics at top, charts in middle, list at bottom.
