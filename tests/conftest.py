"""
Pytest Fixtures and Test Setup.
Configures in-memory SQLite database, fresh test sessions, and FastAPI test client.
"""
import pytest
import sys
from pathlib import Path
from datetime import date, datetime

# Append project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.database.session import Base
from src.database.models import (
    Location, Role, Level, CompensationBand, Employee,
    SalaryRecord, PerformanceEvidence, Tenure, Promotion,
    AdjustmentProposal, ApprovalEvent, ExchangeRate,
    RoleComparabilityRationale, GroundTruthRecord
)
from src.api.main import app
from src.database.session import get_db

# In-memory SQLite engine for tests
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False}
)

@event.listens_for(TEST_ENGINE, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(scope="session")
def setup_test_db():
    """Creates database schema once for the test session."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture(scope="function")
def db_session(setup_test_db):
    """Provides a transactional session rolled back after every test."""
    connection = TEST_ENGINE.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient wired to the test database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sample_master_data(db_session):
    """Populates basic master data (Role, Level, Location, FX, Bands)."""
    loc = Location(
        location_id="LOC-NYC",
        location_name="New York, USA",
        country="USA",
        currency="USD",
        geo_tier="Tier-1",
        cost_of_living_index=1.0
    )
    role = Role(
        role_id="ROLE-SWE",
        role_title="Software Engineer",
        job_family="Engineering",
        job_function="Backend"
    )
    level = Level(
        level_id="LVL-L3",
        level_code="L3",
        level_name="Senior",
        rank=3
    )
    band = CompensationBand(
        band_id="BAND-ROLE-SWE-LVL-L3-LOC-NYC-2026",
        role_id="ROLE-SWE",
        level_id="LVL-L3",
        location_id="LOC-NYC",
        currency="USD",
        min_salary=120000.0,
        mid_salary=150000.0,
        max_salary=180000.0,
        effective_start_date=date(2026, 1, 1),
        effective_end_date=date(2026, 12, 31),
        status="ACTIVE"
    )
    fx = ExchangeRate(
        exchange_rate_id="FX-GBP-USD-2026",
        from_currency="GBP",
        to_currency="USD",
        rate=1.30,
        effective_start_date=date(2026, 1, 1),
        effective_end_date=date(2026, 12, 31)
    )
    db_session.add_all([loc, role, level, band, fx])
    db_session.flush()
    return {"location": loc, "role": role, "level": level, "band": band, "fx": fx}
