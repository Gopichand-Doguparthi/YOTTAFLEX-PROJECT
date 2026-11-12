"""
View 11: Audit Trail & Compliance Ledger View.
Displays immutable append-only state mutations, user actors, and chronological events.
Supports download as PDF, CSV, and Excel.
"""
import io
from typing import List
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import ApprovalEvent, AdjustmentProposal, Employee
from src.dashboard.views.helpers import format_actor_name, fmt_usd


def _pdf_escape(text: str) -> str:
    """Sanitize and escape text for PDF WinAnsi string literals."""
    clean = str(text).replace("\r", " ").replace("\n", " ")
    clean = clean.encode("latin-1", "replace").decode("latin-1")
    return clean.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pure_pdf(title: str, df: pd.DataFrame) -> bytes:
    """
    Generates a valid multi-page Landscape A4 PDF 1.4 document in pure Python
    without requiring external PDF libraries.
    """
    page_w, page_h = 842.0, 595.0
    margin_l, margin_r, margin_t, margin_b = 24.0, 24.0, 42.0, 28.0
    usable_w = page_w - margin_l - margin_r

    headers = list(df.columns)
    # Proportional column widths tailored to audit columns
    weight_map = {
        "Event ID": 1.35,
        "Timestamp": 1.35,
        "Entity": 1.25,
        "Entity ID": 1.25,
        "Event Type": 1.45,
        "Actor": 1.15,
        "Actor Role": 0.95,
        "Notes": 2.25,
    }
    weights = [weight_map.get(h, 1.0) for h in headers]
    total_w = sum(weights)
    col_widths = [(w / total_w) * usable_w for w in weights]

    font_size = 7.0
    header_font_size = 7.5
    row_h = 15.0
    header_h = 18.0
    char_w = 3.85  # Approximate average glyph width at 7pt Helvetica

    def fit_text(val: str, width_pt: float) -> str:
        max_chars = max(4, int((width_pt - 6.0) / char_w))
        s = str(val).replace("\r", " ").replace("\n", " ").strip()
        if len(s) > max_chars:
            return s[: max_chars - 3] + "..."
        return s

    rows = df.astype(str).values.tolist()
    start_y_first_page = page_h - margin_t - 34.0
    start_y_other_page = page_h - margin_t - 10.0

    # Paginate rows
    pages_rows: List[List[List[str]]] = []
    idx = 0
    while idx < len(rows) or not pages_rows:
        top_y = start_y_first_page if not pages_rows else start_y_other_page
        avail_h = top_y - margin_b - header_h
        max_rows = max(1, int(avail_h // row_h))
        pages_rows.append(rows[idx : idx + max_rows])
        idx += max_rows

    total_pages = len(pages_rows)

    # Assemble PDF objects
    objects: List[bytes] = []

    def add_obj(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    # 1: Catalog, 2: Pages placeholder (will fill kids after pages), 3: F1, 4: F2
    catalog_id = add_obj(b"")  # placeholder
    pages_id = add_obj(b"")    # placeholder
    f1_id = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    f2_id = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    page_obj_ids = []
    for p_idx, p_rows in enumerate(pages_rows):
        cmds: List[str] = []

        # Title on first page
        if p_idx == 0:
            cmds.append("0.10 0.12 0.21 rg")
            cmds.append(f"BT /F2 13 Tf {margin_l:.1f} {page_h - margin_t + 8:.1f} Td ({_pdf_escape(title)}) Tj ET")
            cmds.append("0.35 0.40 0.48 rg")
            subtitle = f"Total Events: {len(rows):,}   |   Page 1 of {total_pages}"
            cmds.append(f"BT /F1 8 Tf {margin_l:.1f} {page_h - margin_t - 8:.1f} Td ({_pdf_escape(subtitle)}) Tj ET")
            table_top = start_y_first_page
        else:
            table_top = start_y_other_page

        # Table header background
        cmds.append("0.10 0.12 0.21 rg")
        cmds.append(f"{margin_l:.1f} {table_top - header_h:.1f} {usable_w:.1f} {header_h:.1f} re f")

        # Table header text
        cmds.append("1 1 1 rg")
        cx = margin_l
        for h_text, cw in zip(headers, col_widths):
            tx = cx + 3.0
            ty = table_top - header_h + 5.5
            cmds.append(f"BT /F2 {header_font_size:.1f} Tf {tx:.1f} {ty:.1f} Td ({_pdf_escape(fit_text(h_text, cw))}) Tj ET")
            cx += cw

        # Data rows
        curr_y = table_top - header_h
        for r_idx, row in enumerate(p_rows):
            row_bottom = curr_y - row_h
            if r_idx % 2 == 1:
                cmds.append("0.96 0.97 0.99 rg")
                cmds.append(f"{margin_l:.1f} {row_bottom:.1f} {usable_w:.1f} {row_h:.1f} re f")

            # Bottom row border
            cmds.append("0.85 0.87 0.91 RG 0.3 w")
            cmds.append(f"{margin_l:.1f} {row_bottom:.1f} m {margin_l + usable_w:.1f} {row_bottom:.1f} l S")

            cmds.append("0.12 0.14 0.18 rg")
            cx = margin_l
            for cell, cw in zip(row, col_widths):
                tx = cx + 3.0
                ty = row_bottom + 4.5
                cmds.append(f"BT /F1 {font_size:.1f} Tf {tx:.1f} {ty:.1f} Td ({_pdf_escape(fit_text(cell, cw))}) Tj ET")
                cx += cw
            curr_y = row_bottom

        # Page footer
        cmds.append("0.45 0.50 0.58 rg")
        footer = f"CompEquity AI Audit Ledger  —  Page {p_idx + 1} of {total_pages}"
        cmds.append(f"BT /F1 7 Tf {margin_l:.1f} 12.0 Td ({_pdf_escape(footer)}) Tj ET")

        stream_bytes = "\n".join(cmds).encode("latin-1", "replace")
        content_id = add_obj(
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
            + stream_bytes
            + b"\nendstream"
        )
        page_id = add_obj(
            (
                f"<< /Type /Page /Parent {pages_id} 0 R "
                f"/MediaBox [0 0 {page_w:.0f} {page_h:.0f}] "
                f"/Resources << /Font << /F1 {f1_id} 0 R /F2 {f2_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode("ascii")
        )
        page_obj_ids.append(page_id)

    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii")
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_ids)} >>".encode("ascii")

    # Serialize with exact xref byte offsets
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for obj_num, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{obj_num} 0 obj\n".encode("ascii"))
        out.write(body)
        out.write(b"\nendobj\n")

    xref_start = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode("ascii"))

    out.write(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )
    return out.getvalue()


def _to_pdf_bytes(df: pd.DataFrame) -> bytes:
    """Generate a valid PDF from the audit dataframe."""
    return _build_pure_pdf("Audit Trail & Compliance Ledger", df)


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Append-Only Audit Trail & Compliance Ledger")
    st.markdown("Chronological, immutable record of state mutations, proposal lifecycles, pending adjustments, and salary application events.")

    event_type_filter = st.selectbox(
        "Filter by Event / Record Type:",
        [
            "All Events & Pending Adjustments",
            "Pending Adjustments (Awaiting Approval)",
            "All Logged Events",
            "PROPOSAL_CREATED",
            "SUBMITTED_FOR_REVIEW",
            "PROPOSAL_APPROVED",
            "PROPOSAL_REJECTED",
            "SALARY_UPDATED",
        ],
        index=0
    )

    emp_lookup = {
        e[0]: f"{e[1]} {e[2]}"
        for e in db.query(Employee.employee_id, Employee.first_name, Employee.last_name).all()
    }

    pending_props = (
        db.query(AdjustmentProposal)
        .filter(AdjustmentProposal.approval_status.in_(["PENDING_REVIEW", "DRAFT"]))
        .order_by(AdjustmentProposal.created_at.desc())
        .all()
    )

    pending_rows = [
        {
            "Event ID": f"PEND-{p.proposal_id}",
            "Timestamp": str(p.created_at)[:19] if p.created_at else str(p.proposed_effective_date),
            "Entity": "Pending Adjustment",
            "Entity ID": p.proposal_id,
            "Event Type": f"Pending ({p.approval_status.replace('_', ' ').title()})",
            "Actor": format_actor_name(p.created_by, fallback="HR Partner"),
            "Actor Role": "Pending Review",
            "Notes": (
                f"{emp_lookup.get(p.employee_id, p.employee_id)} ({p.employee_id}) — "
                f"{fmt_usd(p.current_salary)} -> {fmt_usd(p.proposed_salary)} "
                f"({p.reason_code.replace('_', ' ').title()}, Eff: {p.proposed_effective_date})"
            ),
        }
        for p in pending_props
    ]

    if event_type_filter == "Pending Adjustments (Awaiting Approval)":
        event_rows = []
        combined_rows = pending_rows
    else:
        query = db.query(ApprovalEvent).order_by(ApprovalEvent.timestamp.desc())
        if event_type_filter not in ("All Events & Pending Adjustments", "All Logged Events"):
            query = query.filter(ApprovalEvent.event_type == event_type_filter)
        events = query.all()
        event_rows = [
            {
                "Event ID": e.event_id,
                "Timestamp": str(e.timestamp)[:19],
                "Entity": e.entity_name,
                "Entity ID": e.entity_id,
                "Event Type": e.event_type.replace("_", " ").title(),
                "Actor": format_actor_name(e.actor_id, fallback="System"),
                "Actor Role": e.actor_role.replace("_", " ").title(),
                "Notes": e.notes or ""
            }
            for e in events
        ]
        if event_type_filter == "All Events & Pending Adjustments":
            combined_rows = pending_rows + event_rows
        else:
            combined_rows = event_rows

    if not combined_rows:
        st.info("No audit events or pending adjustments match the selected filter.")
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("Records in View", f"{len(combined_rows):,}")
    m2.metric("Logged Audit Events", f"{len(event_rows):,}")
    m3.metric("Pending Adjustments", f"{len(pending_rows):,}")
    st.markdown("---")

    df_audit = pd.DataFrame(combined_rows)

    st.subheader("Audit Trail & Pending Adjustments Ledger")
    st.dataframe(df_audit, use_container_width=True, hide_index=True)

    # Download options
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
