# AI Prompt History & Development Conversations

**RECONSTRUCTED SAMPLE — NOT AN EXACT EXPORT OF ACTUAL AI CONVERSATIONS.**

---

**Conversation 1**

**Me:** How should I start developing this project?

**ChatGPT:** First, understand the requirements, identify the main entities, select the technology stack, and plan the application architecture.

---

**Conversation 2**

**Me:** What are the key business requirements for the compensation fairness system?

**Claude AI:** You need to benchmark employee salaries against role, level, location, performance, and tenure to identify unexplained pay disparities without using demographic attributes, while handling edge cases and remediation proposals.

---

**Conversation 3**

**Me:** Which technology stack is best suited for this application?

**Antigravity AI:** A Python stack using FastAPI for REST APIs, SQLAlchemy 2.0 with PostgreSQL/SQLite for data storage, Alembic for migrations, Streamlit and Plotly for the dashboard, and Pytest for testing.

---

**Conversation 4**

**Me:** How should the database schema be designed for compensation data?

**ChatGPT:** Create relational models for locations, roles, levels, compensation bands, employees, salary records, tenure, performance evidence, promotions, proposals, approval events, and review cases with strict foreign keys and check constraints.

---

**Conversation 5**

**Me:** How can I generate 5,000 synthetic employee records deterministically?

**Claude AI:** Build a generator in Python using fixed random seed 20261022 with NumPy and Pandas to reproducibly create 5,000 employees, 3-year salary histories, and injected edge cases like expired bands and missing currency rates.

---

**Conversation 6**

**Me:** How should the FastAPI backend be structured?

**Antigravity AI:** Organize endpoints into modular APIRouter files for employees, bands, disparities, exceptions, proposals, and review cases, using Pydantic v2 schemas for strict request and response validation.

---

**Conversation 7**

**Me:** How do I manage database migrations and schema changes cleanly?

**ChatGPT:** Use SQLAlchemy 2.0 declarative models with composite indexes, and use Alembic migration scripts to manage versioned database upgrades for initial schema creation and new tables like review cases.

---

**Conversation 8**

**Me:** How should API endpoints be secured?

**Claude AI:** Implement HS256-signed JWT bearer tokens with expiration checks in `src/api/auth.py`, and enforce role-based access control for roles such as HR_PARTNER, MANAGER, and SYSTEM_ADMIN.

---

**Conversation 9**

**Me:** How should part-time employee salaries be normalized for fair comparison?

**Antigravity AI:** Annualize the base salary according to pay frequency and divide it by the employee's FTE fraction so that part-time earnings are scaled to a 1.0 Full-Time Equivalent baseline.

---

**Conversation 10**

**Me:** How do we handle international employees paid in different currencies?

**ChatGPT:** Query effective-dated exchange rates matching the salary effective date to convert local currency to USD, and raise an explicit exception if a valid rate is missing instead of defaulting to 1.0.

---

**Conversation 11**

**Me:** How do I calculate compa-ratio and within-band position accurately?

**Claude AI:** Divide the normalized USD salary by the USD-converted band midpoint for compa-ratio, and calculate `(salary - min) / (max - min)` to determine quartile position within the band.

---

**Conversation 12**

**Me:** How does the disparity detection engine identify unexplained pay gaps?

**Antigravity AI:** It benchmarks an employee against their peer cohort median and flags an unexplained disparity if pay is more than 15% below median despite high performance ratings and established company tenure.

---

**Conversation 13**

**Me:** What views should the Streamlit dashboard provide?

**ChatGPT:** Build an executive overview with KPI cards, deep-dive views for compensation bands and compa-ratios, exception diagnostics for the 5 negative edge cases, proposal management, and an audit trail ledger.

---

**Conversation 14**

**Me:** How should flagged disparities be tracked for human investigation?

**Claude AI:** Use a `ReviewCase` model with statuses OPEN, IN_REVIEW, ESCALATED, and RESOLVED, allowing HR partners to record notes and investigate anomalies before any salary adjustments are made.

---

**Conversation 15**

**Me:** How do we create and manage salary adjustment proposals?

**Antigravity AI:** Create `AdjustmentProposal` records with proposed salary, justification notes, and reason codes like INTERNAL_EQUITY, assigning sequential IDs such as ADJ-2026-000001 synced from the database.

---

**Conversation 16**

**Me:** How should the proposal approval workflow and governance be enforced?

**ChatGPT:** Implement state transitions from DRAFT to PENDING_REVIEW to APPROVED or REJECTED, enforce authorized approver roles, and strictly prohibit proposal creators from approving their own proposals.

---

**Conversation 17**

**Me:** How do we ensure all compensation modifications are auditable?

**Claude AI:** Log an append-only event into `approval_events` for every proposal creation, submission, review decision, and applied adjustment with actor IDs, roles, timestamps, and state snapshots.

---

**Conversation 18**

**Me:** How should the testing suite be organized to prevent regressions?

**Antigravity AI:** Write Pytest test suites covering normalization, compa-ratios, the 5 mandatory edge cases, non-USD band conversions, API routes, and reproducibility verification using SQLite in-memory fixtures.

---

**Conversation 19**

**Me:** What security measures should be implemented across the application?

**ChatGPT:** Restrict CORS origins to localhost, use constant-time comparison for JWT verification, validate inputs with Pydantic schemas, and rely on SQLAlchemy parameterized queries to prevent SQL injection.

---

**Conversation 20**

**Me:** How do I verify that the full project is production-ready?

**Claude AI:** Run the decoupled ground-truth evaluation script to verify 100% precision and recall across all 5,000 records, confirm all 52 Pytest tests pass, and test the Streamlit dashboard end to end.
