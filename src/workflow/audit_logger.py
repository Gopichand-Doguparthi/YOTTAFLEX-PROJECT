"""
Append-Only Audit Logging Service.
Logs all state changes, proposal submissions, approvals, rejections, and exception discoveries.
"""
from datetime import datetime
import json
from typing import Optional, Any
from sqlalchemy.orm import Session
from src.database.models import ApprovalEvent


class AuditLogger:
    """Manages append-only audit trail logging to the database."""

    _counter = 0

    @classmethod
    def generate_event_id(cls, event_date: Optional[datetime] = None) -> str:
        """Generates deterministic unique sequence ID: EVT-YYYYMMDD-000001."""
        dt = event_date or datetime.utcnow()
        cls._counter += 1
        return f"EVT-{dt.strftime('%Y%m%d')}-{cls._counter:06d}"

    @classmethod
    def log_event(
        cls,
        session: Session,
        entity_name: str,
        entity_id: str,
        event_type: str,
        actor_id: str,
        actor_role: str,
        new_state: Any,
        old_state: Optional[Any] = None,
        notes: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> ApprovalEvent:
        """Creates and persists an immutable audit event."""
        event_time = timestamp or datetime.utcnow()
        prefix = f"EVT-{event_time.strftime('%Y%m%d')}-"
        existing_ids = session.query(ApprovalEvent.event_id).filter(
            ApprovalEvent.event_id.like(f"{prefix}%")
        ).all()
        max_seq = 0
        for (eid,) in existing_ids:
            suffix = eid[len(prefix):]
            if suffix.isdigit():
                max_seq = max(max_seq, int(suffix))
        if cls._counter < max_seq:
            cls._counter = max_seq
        event_id = cls.generate_event_id(event_time)

        old_str = json.dumps(old_state) if isinstance(old_state, (dict, list)) else (str(old_state) if old_state is not None else None)
        new_str = json.dumps(new_state) if isinstance(new_state, (dict, list)) else str(new_state)

        event = ApprovalEvent(
            event_id=event_id,
            entity_name=entity_name,
            entity_id=entity_id,
            event_type=event_type,
            actor_id=actor_id,
            actor_role=actor_role,
            old_state=old_str,
            new_state=new_str,
            notes=notes,
            timestamp=event_time
        )
        session.add(event)
        session.flush()
        return event
