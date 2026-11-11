"""
Evaluation API Endpoints.
Outputs precision, recall, F1-score, confusion matrix, and coverage metrics.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.evaluation.evaluator import EvaluationEngine
from src.api.schemas import EvaluationSummarySchema

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


@router.get("", response_model=EvaluationSummarySchema)
def get_evaluation_metrics(db: Session = Depends(get_db)):
    """Executes objective evaluation against independent ground truth and returns statistical metrics."""
    return EvaluationEngine.evaluate(db)
