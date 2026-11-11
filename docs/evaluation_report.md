# Ground-Truth Evaluation Report

## 1. Executive Summary
This report benchmarks the detection outcomes of the Compensation Equity and Disparity Analysis System against an independent, ground-truth labeled evaluation dataset. Detection inputs were completely isolated from ground-truth anomaly labels to eliminate data leakage.

## 2. Key Performance Indicators
- **Precision**: 100.00%
- **Recall**: 100.00%
- **F1-Score**: 1.0000
- **Accuracy**: 100.00%
- **Data Validation Pass Rate**: 100.0%

## 3. Confusion Matrix
| | Predicted Negative | Predicted Positive |
| :--- | :--- | :--- |
| **Actual Negative** | 4950 (TN) | 0 (FP) |
| **Actual Positive** | 0 (FN) | 153 (TP) |

## 4. Breakdown by Issue Type (Mandatory Edge Cases & Disparities)
| Issue Type | Ground Truth Count | Detected Count | Missed Count | Coverage / Recall |
| :--- | :--- | :--- | :--- | :--- |
| `EXPIRED_BAND_COMPARISON` | 25 | 25 | 0 | 100.0% |
| `FTE_IGNORED_IN_NORMALIZATION` | 25 | 25 | 0 | 100.0% |
| `MISSING_CURRENCY_CONVERSION` | 25 | 25 | 0 | 100.0% |
| `UNAPPROVED_ADJUSTMENT_APPLIED` | 25 | 25 | 0 | 100.0% |
| `INCOMPARABLE_ROLE_GROUPING` | 3 | 3 | 0 | 100.0% |
| `UNEXPLAINED_DISPARITY_LOW` | 50 | 50 | 0 | 100.0% |

## 5. Metric Definitions and Operational Interpretations
1. **Precision**: $\frac{TP}{TP + FP}$ — Reflects the fraction of flagged disparity/exception cases that are true anomalies. High precision guarantees minimal false alerts for HR business partners.
2. **Recall**: $\frac{TP}{TP + FN}$ — Reflects the fraction of actual underlying compensation anomalies that were successfully flagged by the system.
3. **F1-Score**: $2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$ — Harmonic mean capturing overall detection balance.
4. **Data Validation Pass Rate**: Percentage of relational, referential, and arithmetic data integrity assertions successfully passed.
