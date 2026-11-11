"""
Database engine and session management.
Supports both PostgreSQL (production/docker) and SQLite (embedded/testing).
Enforces foreign keys and WAL mode on SQLite.
"""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from src.config import DATABASE_URL

# Normalize sqlite URL if relative
db_url = DATABASE_URL
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True
)

# Enable foreign keys on SQLite connections
if db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for FastAPI or scripts to obtain a transactional session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes all registered tables in the database."""
    from src.database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
