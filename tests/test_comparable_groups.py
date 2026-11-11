"""
Tests for Comparable Groups Cohort Segmentation and Role Comparability Rationales.
"""
import pytest
from src.engine.comparable_groups import ComparableGroupEngine, IncomparableRoleGroupingException


def test_identical_roles_are_always_comparable():
    engine = ComparableGroupEngine(rationales=[])
    is_valid, reason = engine.validate_role_pair_comparability("ROLE-SWE", "ROLE-SWE")
    assert is_valid is True
    assert "Identical" in reason


def test_approved_role_comparability_rationale():
    rationales = [
        {
            "role_id_a": "ROLE-SWE",
            "role_id_b": "ROLE-FSE",
            "is_comparable": True,
            "documented_rationale": "Equivalent core software engineering competencies."
        }
    ]
    engine = ComparableGroupEngine(rationales=rationales)

    is_valid, reason = engine.validate_role_pair_comparability("ROLE-SWE", "ROLE-FSE")
    assert is_valid is True
    assert "Approved rationale" in reason

    # Bidirectional symmetry
    is_valid_rev, _ = engine.validate_role_pair_comparability("ROLE-FSE", "ROLE-SWE")
    assert is_valid_rev is True


def test_unapproved_incomparable_roles_rejected():
    rationales = [
        {
            "role_id_a": "ROLE-SWE",
            "role_id_b": "ROLE-FAC",
            "is_comparable": False,
            "documented_rationale": "Incomparable disciplines."
        }
    ]
    engine = ComparableGroupEngine(rationales=rationales)

    is_valid, reason = engine.validate_role_pair_comparability("ROLE-SWE", "ROLE-FAC")
    assert is_valid is False
    assert "Documented exclusion" in reason

    # Completely unmapped pair
    is_valid_unmapped, reason_unmapped = engine.validate_role_pair_comparability("ROLE-SWE", "ROLE-TAX")
    assert is_valid_unmapped is False
    assert "No documented comparability rationale" in reason_unmapped


def test_cohort_statistics_computation():
    engine = ComparableGroupEngine()
    records = [
        {"role_id": "ROLE-SWE", "level_id": "LVL-L3", "location_id": "LOC-NYC", "normalized_salary": 140000.0},
        {"role_id": "ROLE-SWE", "level_id": "LVL-L3", "location_id": "LOC-NYC", "normalized_salary": 150000.0},
        {"role_id": "ROLE-SWE", "level_id": "LVL-L3", "location_id": "LOC-NYC", "normalized_salary": 160000.0},
        {"role_id": "ROLE-SWE", "level_id": "LVL-L3", "location_id": "LOC-NYC", "normalized_salary": 170000.0},
    ]

    stats = engine.compute_cohort_statistics(records, min_cohort_size=3)
    key = "ROLE-SWE::LVL-L3::LOC-NYC"
    assert key in stats
    assert stats[key]["count"] == 4
    assert stats[key]["median_salary"] == 155000.0
    assert stats[key]["min_salary"] == 140000.0
    assert stats[key]["max_salary"] == 170000.0
    assert stats[key]["is_sufficient"] is True


def test_small_cohort_insufficient_evidence():
    engine = ComparableGroupEngine()
    records = [
        {"role_id": "ROLE-PM", "level_id": "LVL-L5", "location_id": "LOC-BER", "normalized_salary": 180000.0},
        {"role_id": "ROLE-PM", "level_id": "LVL-L5", "location_id": "LOC-BER", "normalized_salary": 190000.0},
    ]
    stats = engine.compute_cohort_statistics(records, min_cohort_size=3)
    key = "ROLE-PM::LVL-L5::LOC-BER"
    assert stats[key]["is_sufficient"] is False
    assert stats[key]["status"] == "INSUFFICIENT_EVIDENCE"
