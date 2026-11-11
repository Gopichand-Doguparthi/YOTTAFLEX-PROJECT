"""
CLI Script to execute ground-truth evaluation and generate evaluation report.
"""
import argparse
import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.session import SessionLocal
from src.evaluation.evaluator import EvaluationEngine
from src.validation.data_validator import DataValidator


def main():
    parser = argparse.ArgumentParser(description="Run Evaluation against Ground Truth.")
    parser.add_argument("--output-report", type=str, default=str(PROJECT_ROOT / "docs" / "evaluation_report.md"))
    args = parser.parse_args()

    print("Running evaluation engine against independent ground truth...")
    session = SessionLocal()
    try:
        eval_results = EvaluationEngine.evaluate(session)
        val_results = DataValidator.run_all_checks(session)

        om = eval_results["overall_metrics"]
        cm = om["confusion_matrix"]

        print("\n================ EVALUATION SUMMARY ================")
        print(f"Total Ground Truth Records Evaluated : {eval_results['total_ground_truth_samples']}")
        print(f"Total Operational Exceptions Detected: {eval_results['total_exceptions_detected']}")
        print(f"Total Disparities Detected           : {eval_results['total_disparities_detected']}")
        print(f"Overall Precision                    : {om['precision'] * 100:.2f}%")
        print(f"Overall Recall                       : {om['recall'] * 100:.2f}%")
        print(f"Overall F1-Score                     : {om['f1_score']:.4f}")
        print(f"Overall Accuracy                     : {om['accuracy'] * 100:.2f}%")
        print(f"Confusion Matrix (TN, FP, FN, TP)    : [{cm['tn']}, {cm['fp']}, {cm['fn']}, {cm['tp']}]")
        print(f"Data Validation Pass Rate            : {val_results['pass_rate_pct']}%\n")

        print("Per-Issue Exception Detection Coverage:")
        for itype, stats in eval_results["per_issue_metrics"].items():
            print(f"  - {itype:<32}: {stats['recall_coverage_pct']:>6.1f}% ({stats['detected_count']}/{stats['ground_truth_count']})")

        # Generate docs/evaluation_report.md
        report_path = Path(args.output_report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Ground-Truth Evaluation Report\n\n")
            f.write("## 1. Executive Summary\n")
            f.write("This report benchmarks the detection outcomes of the Compensation Equity and Disparity Analysis System against an independent, ground-truth labeled evaluation dataset. Detection inputs were completely isolated from ground-truth anomaly labels to eliminate data leakage.\n\n")

            f.write("## 2. Key Performance Indicators\n")
            f.write(f"- **Precision**: {om['precision'] * 100:.2f}%\n")
            f.write(f"- **Recall**: {om['recall'] * 100:.2f}%\n")
            f.write(f"- **F1-Score**: {om['f1_score']:.4f}\n")
            f.write(f"- **Accuracy**: {om['accuracy'] * 100:.2f}%\n")
            f.write(f"- **Data Validation Pass Rate**: {val_results['pass_rate_pct']}%\n\n")

            f.write("## 3. Confusion Matrix\n")
            f.write("| | Predicted Negative | Predicted Positive |\n")
            f.write("| :--- | :--- | :--- |\n")
            f.write(f"| **Actual Negative** | {cm['tn']} (TN) | {cm['fp']} (FP) |\n")
            f.write(f"| **Actual Positive** | {cm['fn']} (FN) | {cm['tp']} (TP) |\n\n")

            f.write("## 4. Breakdown by Issue Type (Mandatory Edge Cases & Disparities)\n")
            f.write("| Issue Type | Ground Truth Count | Detected Count | Missed Count | Coverage / Recall |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            for itype, stats in eval_results["per_issue_metrics"].items():
                f.write(f"| `{itype}` | {stats['ground_truth_count']} | {stats['detected_count']} | {stats['missed_count']} | {stats['recall_coverage_pct']:.1f}% |\n")

            f.write("\n## 5. Metric Definitions and Operational Interpretations\n")
            f.write("1. **Precision**: $\\frac{TP}{TP + FP}$ — Reflects the fraction of flagged disparity/exception cases that are true anomalies. High precision guarantees minimal false alerts for HR business partners.\n")
            f.write("2. **Recall**: $\\frac{TP}{TP + FN}$ — Reflects the fraction of actual underlying compensation anomalies that were successfully flagged by the system.\n")
            f.write("3. **F1-Score**: $2 \\times \\frac{\\text{Precision} \\times \\text{Recall}}{\\text{Precision} + \\text{Recall}}$ — Harmonic mean capturing overall detection balance.\n")
            f.write("4. **Data Validation Pass Rate**: Percentage of relational, referential, and arithmetic data integrity assertions successfully passed.\n")

        print(f"\nDetailed evaluation report generated at: {report_path}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
