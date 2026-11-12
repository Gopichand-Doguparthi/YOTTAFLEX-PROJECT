"""
View 11: Audit Trail & Compliance Ledger View.
Displays immutable append-only state mutations, user actors, and chronological events.
Supports download as PDF, CSV, and Excel.
"""
import io
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import ApprovalEvent


def _to_pdf_bytes(df: pd.DataFrame) -> bytes:
    """Generate a simple PDF from the audit dataframe using reportlab if available, else fallback to text."""
    try:
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=20)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("Audit Trail & Compliance Ledger", styles["Title"]))
        elements.append(Spacer(1, 12))

        # Table data
        headers = list(df.columns)
        rows = [headers] + df.astype(str).values.tolist()

        table = Table(rows, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1f36")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(table)
        doc.build(elements)
        return buffer.getvalue()
    except ImportError:
        # Fallback: plain text
        return df.to_string(index=False).encode("utf-8")


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Append-Only Audit Trail & Compliance Ledger")
    st.markdown("Chronological, immutable record of state mutations, proposal lifecycles, and salary application events.")

    event_type_filter = st.selectbox(
        "Filter by Event Type:",
        ["All Events", "PROPOSAL_CREATED", "SUBMITTED_FOR_REVIEW", "PROPOSAL_APPROVED", "PROPOSAL_REJECTED", "SALARY_UPDATED"],
        index=0
    )

    query = db.query(ApprovalEvent).order_by(ApprovalEvent.timestamp.desc())
    if event_type_filter != "All Events":
        query = query.filter(ApprovalEvent.event_type == event_type_filter)

    events = query.all()

    if not events:
        st.info("No audit events recorded.")
        return

    st.metric("Total Logged Events In Query", f"{len(events):,}")
    st.markdown("---")

    event_data = [
        {
            "Event ID": e.event_id,
            "Timestamp": str(e.timestamp)[:19],
            "Entity": e.entity_name,
            "Entity ID": e.entity_id,
            "Event Type": e.event_type,
            "Actor ID": e.actor_id,
            "Actor Role": e.actor_role,
            "Notes": e.notes or ""
        }
        for e in events
    ]

    df_audit = pd.DataFrame(event_data)

    st.subheader("Immutable Audit Events Table")
    st.dataframe(df_audit, use_container_width=True)

    # ── Download options ──
    st.markdown("---")
    st.subheader("Download Audit History")
    dl_col1, dl_col2, dl_col3 = st.columns(3)

    with dl_col1:
        csv_bytes = df_audit.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download as CSV",
            data=csv_bytes,
            file_name="audit_trail.csv",
            mime="text/csv"
        )

    with dl_col2:
        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
            df_audit.to_excel(writer, index=False, sheet_name="Audit Trail")
        st.download_button(
            label="Download as Excel",
            data=excel_buf.getvalue(),
            file_name="audit_trail.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with dl_col3:
        pdf_bytes = _to_pdf_bytes(df_audit)
        st.download_button(
            label="Download as PDF",
            data=pdf_bytes,
            file_name="audit_trail.pdf",
            mime="application/pdf"
        )
