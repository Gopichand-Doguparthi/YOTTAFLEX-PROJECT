"""
View 11: Audit Trail & Compliance Ledger View.
Displays immutable append-only state mutations, user actors, and chronological events.
"""
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import ApprovalEvent


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

    events = query.limit(500).all()

    if not events:
        st.info("No audit events recorded.")
        return

    st.metric("Total Logged Events In Query", len(events))
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

    st.subheader("Immutable Audit Events Table")
    st.dataframe(pd.DataFrame(event_data), use_container_width=True)
