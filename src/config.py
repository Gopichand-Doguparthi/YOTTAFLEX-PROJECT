"""
Global Application Configuration.
Loads settings from environment variables or .env file with safe defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/compensation_equity.db")
POSTGRES_DATABASE_URL = os.getenv("POSTGRES_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/compensation_equity")

# Application Settings
REPORTING_CURRENCY = os.getenv("REPORTING_CURRENCY", "USD")
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "20261022"))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Server / API Settings
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8501"))
API_BASE_URL = os.getenv("API_BASE_URL", f"http://{API_HOST}:{API_PORT}")

# Analytical Rules & Thresholds
COMPA_RATIO_MIN = float(os.getenv("COMPA_RATIO_MIN", "0.80"))
COMPA_RATIO_MAX = float(os.getenv("COMPA_RATIO_MAX", "1.20"))
DISPARITY_THRESHOLD_PERCENT = float(os.getenv("DISPARITY_THRESHOLD_PERCENT", "15.0"))
PERFORMANCE_EXEMPLARY_RATING = float(os.getenv("PERFORMANCE_EXEMPLARY_RATING", "3.5"))
MIN_COMPARABLE_GROUP_SIZE = int(os.getenv("MIN_COMPARABLE_GROUP_SIZE", "3"))

# Data Paths
DATA_DIR = PROJECT_ROOT / "data"
STARTER_DATA_DIR = DATA_DIR / "starter"
FULL_DATA_DIR = DATA_DIR / "full"
DOCS_DIR = PROJECT_ROOT / "docs"
