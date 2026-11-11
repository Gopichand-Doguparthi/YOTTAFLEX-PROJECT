"""
Tests for Append-Only Audit Logging.
"""
from datetime import datetime
from src.database.models import ApprovalEvent
from src.workflow.audit_logger import AuditLogger


def test_audit_event_logging(db_session):
    AuditLogger._counter = 0

    event1 = AuditLogger.log_event(
        session=db_session,
        entity_name="AdjustmentProposal",
        entity_id="ADJ-2026-000001",
        event_type="PROPOSAL_CREATED",
        actor_id="hr.specialist@company.org",
        actor_role="HR_PARTNER",
        new_state={"status": "DRAFT", "proposed_salary": 140000.0},
        notes="Created draft proposal."
    )

    assert event1.event_id.startswith("EVT-")
    assert event1.actor_role == "HR_PARTNER"
    assert event1.event_type == "PROPOSAL_CREATED"

    event2 = AuditLogger.log_event(
        session=db_session,
        entity_name="AdjustmentProposal",
        entity_id="ADJ-2026-000001",
        event_type="PROPOSAL_APPROVED",
        actor_id="vp.engineering@company.org",
        actor_role="MANAGER",
        old_state={"status": "PENDING_REVIEW"},
        new_state={"status": "APPROVED"},
        notes="Executive approval granted."
    )

    assert event2.event_id != event1.event_id

    # Verify queryable from DB
    logged_events = db_session.query(ApprovalEvent).filter_by(entity_id="ADJ-2026-000001").all()
    assert len(logged_events) == 2
