"""
Data Validation and Quality Assurance API Endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.validation.data_validator import DataValidator
from src.validation.reproducibility import ReproducibilityVerifier

router = APIRouter(prefix="/validation", tags=["Validation & Quality"])


@router.get("/integrity")
def get_validation_report(db: Session = Depends(get_db)):
    """Runs database relational, arithmetic, date ordering, and enum checks."""
    return DataValidator.run_all_checks(db)


@router.get("/reproducibility")
def get_reproducibility_report(scale: str = "starter", seed: int = 20261022):
    """Executes dual-run generator comparison and returns reproducibility report."""
    return ReproducibilityVerifier.verify(seed=seed, scale=scale)
