# System Architecture Document

## Project Title
**Compensation Equity and Disparity Analysis System**

## 1. Executive Summary & Objective
The Compensation Equity and Disparity Analysis System provides an automated, auditable, and transparent analytics engine designed to benchmark employee salaries against role, level, location, and documented job-related factors (tenure, performance, promotions) to uncover unexplained compensation disparities while honoring complex real-world edge cases.

## 2. High-Level Architecture
The system follows a clean modular layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  - Streamlit Executive & Operational Dashboard (13 Views)   │
│  - Interactive Plotly Visualizations & Metric Scorecards    │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / Client Service
┌──────────────────────────────▼──────────────────────────────┐
│                    Service & API Layer                      │
│  - FastAPI REST Application                                 │
│  - Pydantic v2 Request/Response Validation Schemas          │
│  - Exception & Validation Endpoints                         │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                 Core Domain & Business Engine               │
│  - Currency Normalizer (Effective-dated FX with exceptions) │
│  - FTE Normalizer (Full-Time Equivalent scaling)            │
│  - Compa-Ratio & Within-Band Position Evaluator             │
│  - Comparable Group Segmenter & Rationale Validator         │
│  - Multi-Factor Disparity Detection Engine                  │
│  - Mandatory Edge Case Detection Suite                      │
│  - Adjustment Proposal Workflow & Append-Only Audit Logger  │
│  - Ground Truth Evaluator & Model Diagnostics               │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                   Data & Persistence Layer                  │
│  - SQLAlchemy 2.0 ORM Models & Session Factory              │
│  - PostgreSQL (Primary) / SQLite (Embedded/Zero-Dep)        │
│  - Alembic Schema Migrations                                │
│  - Synthetic Generator (Deterministic seed 20261022)        │
│  - CSV / JSON / SQL Exporters & Validation Suite            │
└─────────────────────────────────────────────────────────────┘
```

## 3. Technology Stack Rationale
1. **Python 3.11 / 3.8+ compatibility**: Robust mathematical, data manipulation, and web backend ecosystem.
2. **PostgreSQL & SQLite Dual-Support**: PostgreSQL configured as the production primary database via Docker Compose and SQLAlchemy connection pooling; SQLite available out-of-the-box for standalone zero-configuration local runs and lightning-fast automated test fixtures.
3. **FastAPI & Pydantic**: Asynchronous, high-throughput REST API with automatic OpenAPI documentation and strict data typing.
4. **Streamlit & Plotly**: Rich, interactive dashboards with deep-dive drill-downs, filtering, and real-time computation without complex frontend build chains.
5. **SQLAlchemy 2.0 & Alembic**: Industry standard database abstraction, relational schema migrations, declarative constraints, and transactional consistency.
6. **Pandas & NumPy**: High-performance vectorized calculation for data generation, normalization, and comparable group cohort statistics.

## 4. Key Architectural Decisions
- **Decoupled Ground Truth**: Ground-truth anomaly labels are isolated in a separate store (`ground_truth.csv` / `ground_truth.json` / `ground_truth_records` table) and NEVER exposed as features to the detection engine.
- **Append-Only Auditing**: State changes to salaries, bands, and proposals emit immutable `ApprovalEvent` records to guarantee an unbroken audit trail.
- **Effective-Dated Validity**: All compensation bands and currency exchange rates enforce start/end date temporal ranges. Comparisons outside validity windows are explicitly trapped as exceptions.
- **Strict ID Nomenclature**:
  - Employee: `EMP-000001`
  - Band: `BAND-<role>-<level>-<location>-2026`
  - Salary Record: `SAL-<employee-id>-2026-01`
  - Adjustment Proposal: `ADJ-2026-000001`
