"""
FastAPI Application Entry Point.
Provides RESTful APIs for the Compensation Equity and Disparity Analysis System.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import (
    analytics, employees, bands, disparities,
    exceptions, proposals, evaluation, validation
)

app = FastAPI(
    title="Compensation Equity and Disparity Analysis System API",
    description="Automated, auditable compensation benchmarking, anomaly detection, and remediation management.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for local Streamlit dashboard and dev tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(analytics.router)
app.include_router(employees.router)
app.include_router(bands.router)
app.include_router(disparities.router)
app.include_router(exceptions.router)
app.include_router(proposals.router)
app.include_router(evaluation.router)
app.include_router(validation.router)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint to verify backend operational readiness."""
    return {
        "status": "healthy",
        "service": "Compensation Equity API",
        "version": "1.0.0"
    }
