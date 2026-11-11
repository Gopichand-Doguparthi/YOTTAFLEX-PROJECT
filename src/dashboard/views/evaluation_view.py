"""
View 13: Ground-Truth Evaluation & Performance Metrics.
Evaluates engine detections against the independent ground-truth dataset.
"""
import streamlit as st
import plotly.express as px
import plotly.figure_factory as ff
import pandas as pd
from sqlalchemy.orm import Session
from src.evaluation.evaluator import EvaluationEngine


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Ground-Truth Evaluation & Model Diagnostics")
    st.markdown("Compares analytical detection results against the isolated, independent ground-truth evaluation dataset.")

    eval_results = EvaluationEngine.evaluate(db)
    om = eval_results["overall_metrics"]
    cm = om["confusion_matrix"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Precision", f"{om['precision'] * 100:.1f}%")
    col2.metric("Recall", f"{om['recall'] * 100:.1f}%")
    col3.metric("F1-Score", f"{om['f1_score']:.4f}")
    col4.metric("Accuracy", f"{om['accuracy'] * 100:.1f}%")

    st.markdown("---")

    col_cm, col_bar = st.columns(2)

    with col_cm:
        st.subheader("Confusion Matrix")
        z = [[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]]
        x = ["Predicted Baseline", "Predicted Anomaly"]
        y = ["Actual Baseline", "Actual Anomaly"]

        fig_cm = ff.create_annotated_heatmap(
            z,
            x=x,
            y=y,
            colorscale="Blues",
            showscale=True
        )
        fig_cm.update_layout(title="Confusion Matrix: Detections vs Ground Truth")
        st.plotly_chart(fig_cm, use_container_width=True)

    with col_bar:
        st.subheader("Exception & Disparity Coverage (Recall)")
        per_issue_data = [
            {
                "Issue Type": k,
                "Coverage (%)": v["recall_coverage_pct"],
                "Detected": v["detected_count"],
                "Ground Truth": v["ground_truth_count"]
            }
            for k, v in eval_results["per_issue_metrics"].items()
        ]
        df_issue = pd.DataFrame(per_issue_data)
        fig_bar = px.bar(
            df_issue,
            x="Issue Type",
            y="Coverage (%)",
            color="Coverage (%)",
            text="Coverage (%)",
            range_y=[0, 115],
            title="Detection Recall Coverage Across Mandatory Edge Cases"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Per-Issue Detailed Metric Breakdown")
    st.dataframe(df_issue, use_container_width=True)
