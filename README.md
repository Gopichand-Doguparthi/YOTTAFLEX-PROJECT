# YottaFlex Employee Compensation Fairness & Salary Analysis System

An auditable compensation benchmarking, multi-factor disparity detection, exception diagnostics, and adjustment-proposal governance system built with **Python**, **SQLAlchemy 2.0**, **FastAPI**, **Streamlit**, and **Plotly**.

---

## Key Capabilities
- **10+ Relational Entities & Strict ID Nomenclature**: `EMP-000001`, `BAND-<role>-<level>-<location>-2026`, `SAL-<employee-id>-2026-01`, `ADJ-2026-000001`.
- **Deterministic Synthetic Dataset (`seed=20261022`)**: Starter (`100` employees) and Full (`5,000` employees, 3-year salary history, promotions, FTE & multi-currency records) with CSV, JSON, and SQL seed exports.
- **Currency & FTE Normalization**: Effective-dated FX conversion to `USD` and `1.0` FTE annualization (`(annual_base * fx_rate) / fte`).
- **Compa-Ratio & Within-Band Position**: Benchmarks normalized USD salaries against USD-converted, effective-dated compensation bands.
- **5 Mandatory Negative Scenarios**:
  1. `EXPIRED_BAND_COMPARISON`
  2. `FTE_IGNORED_IN_NORMALIZATION`
  3. `MISSING_CURRENCY_CONVERSION`
  4. `UNAPPROVED_ADJUSTMENT_APPLIED`
  5. `INCOMPARABLE_ROLE_GROUPING`
- **Proposal & Approval Workflow**: Enforces `DRAFT -> PENDING_REVIEW -> APPROVED / REJECTED`, role-based authorization (`MANAGER`, `HR_PARTNER`, `SYSTEM_ADMIN`, `COMP_COMMITTEE`), self-approval prevention, and append-only `ApprovalEvent` audit trails.
- **Decoupled Ground-Truth Evaluation**: Computes TP, FP, TN, FN, Precision, Recall, and F1-score without leaking ground-truth labels into detection inputs.

---

## Setup & Installation

### 1. Create Virtual Environment & Install Dependencies
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Environment Configuration
Copy `.env.example` to `.env` (defaults to zero-setup local SQLite `sqlite:///./compensation_equity.db`):
```bash
cp .env.example .env
```

### 3. Database Migration & Dataset Generation
Run Alembic migrations (or let the pipeline initialize the schema) and generate the deterministic dataset:
```bash
alembic upgrade head
python scripts/run_generator.py --scale full --seed 20261022
python scripts/run_pipeline.py
```

Verify deterministic reproducibility across two independent runs:
```bash
python scripts/verify_reproducibility.py --scale starter
```

---

## Running the Application

### FastAPI Backend
```bash
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API docs: `http://127.0.0.1:8000/docs`

### Streamlit Dashboard
```bash
streamlit run src/dashboard/app.py --server.port 8501
```
Dashboard URL: `http://127.0.0.1:8501`

### Docker Compose (PostgreSQL + API + Dashboard)
```bash
docker-compose up --build
```

---

## Running Tests
```bash
pytest -v
```

---

## Documentation
- [System Architecture](docs/architecture.md)
- [Database Schema](docs/database_schema.md)
- [Business Rules & Formulas](docs/business_rules.md)
- [Data Dictionary](docs/data_dictionary.md)
- [Assumptions & Operational Parameters](docs/assumptions.md)
- [Evaluation Report](docs/evaluation_report.md)
