"""
Statistical Evaluation and Classification Metrics Module.
Calculates TP, FP, TN, FN, Precision, Recall, Specificity, F1-score, and Confusion Matrices.
"""
from typing import Dict, Any, List


class MetricCalculator:
    """Computes binary and multiclass classification performance metrics."""

    @staticmethod
    def compute_binary_metrics(tp: int, fp: int, tn: int, fn: int) -> Dict[str, Any]:
        """
        Computes standard information retrieval and diagnostic metrics.
        Handles zero-division safely.
        """
        total = tp + fp + tn + fn
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        f1_score = (2.0 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / total if total > 0 else 0.0

        return {
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
            "total_samples": total,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "specificity": round(specificity, 4),
            "f1_score": round(f1_score, 4),
            "accuracy": round(accuracy, 4),
            "confusion_matrix": {
                "tn": tn, "fp": fp,
                "fn": fn, "tp": tp,
                "matrix_2x2": [[tn, fp], [fn, tp]]
            }
        }
