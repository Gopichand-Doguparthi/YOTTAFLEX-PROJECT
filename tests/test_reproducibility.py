"""
Tests for Generator Reproducibility and Deterministic Hashing.
"""
from src.validation.reproducibility import ReproducibilityVerifier


def test_generator_reproducibility():
    results = ReproducibilityVerifier.verify(seed=20261022, scale="starter")
    assert results["is_reproducible"] is True
    assert len(results["mismatches"]) == 0
    assert results["tables_checked"] >= 10

    # Ensure all tables matched hashes
    for tbl, res in results["table_results"].items():
        assert res["is_match"] is True
        assert res["rows_run1"] == res["rows_run2"]
        assert res["sha256_run1"] == res["sha256_run2"]
