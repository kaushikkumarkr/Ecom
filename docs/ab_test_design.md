# A/B Test Design: "Sticky Efficiency" in Checkout Flow

## 1. Context & Hypothesis
**Problem**: Our funnel analysis (`mart_funnel`) shows a 60% drop-off between "Add to Cart" and "Purchase".
**Hypothesis**: Users are abandoning carts because shipping costs are calculated too late in the flow. Showing "Estimated Shipping" on the Cart page (instead of Checkout Step 3) will reduce anxiety and increase conversion.
**Proposed Change**: Implement a "Shipping Estimator" widget on the Cart View.

## 2. Metrics

### Primary Metric (The "North Star")
-   **Checkout Conversion Rate (CVR)**:
    -   *Definition*: Unique Purchasers / Unique Users reaching Cart.
    -   *Goal*: Increase from 40% (baseline) to 42% (relative lift of +5%).

### Secondary Metrics (Context)
-   **Add-to-Cart Rate**: Should remain neutral (check for cannibalization).
-   **Average Order Value (AOV)**: Ensure users aren't buying cheaper items to offset shipping.

### Guardrail Metrics (Do No Harm)
-   **Page Load Time (Cart Page)**: Must not increase by >200ms (latency guardrail).
-   **Customer Support Tickets**: Monitor for "shipping error" tickets.

## 3. Power Analysis & Sample Size
*Assumptions based on historical data:*
-   **Baseline CVR**: 40%
-   **Minimum Detectable Effect (MDE)**: 5% relative lift (Target = 42%)
-   **Significance Level (alpha)**: 0.05 (95% confidence)
-   **Power (1-beta)**: 0.80 (80% power)

**Result**: We need approximately **9,500 users per variant**.
With ~2,000 daily cart users, the test will run for **~10 days**.

## 4. Rollout Plan
1.  **QA**: Internal testing on staging.
2.  **Ramp**: 1% vs 1% (Health Check) -> 50% vs 50% (Full Experiment).
3.  **Duration**: 2 weeks (to capture weekly seasonality).

## 5. Decision Rule
-   **Launch if**: Primary metric shows statistically significant positive lift (>0) AND Guardrails are green.
-   **Rollback if**: Primary metric is neutral/negative OR Page Latency spiked > 200ms.
