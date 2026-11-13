"""
Root entry point for Streamlit Community Cloud deployment.
Streamlit Cloud auto-detects `streamlit_app.py` at the repository root.
"""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Run dashboard
from src.dashboard.app import main

if __name__ == "__main__":
    main()
