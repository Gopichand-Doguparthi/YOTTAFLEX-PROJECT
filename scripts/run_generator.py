"""
CLI Script to generate synthetic data and populate database.
Supports 'starter' and 'full' dataset scales with fixed seed 20261022.
"""
import argparse
import sys
from datetime import date, datetime
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RANDOM_SEED, STARTER_DATA_DIR, FULL_DATA_DIR
from src.generator.synthetic_generator import SyntheticDataGenerator
from src.generator.exporter import DatasetExporter
from src.database.session import SessionLocal, init_db
from src.database.models import (
    Location, Role, Level, CompensationBand, Employee,
    SalaryRecord, PerformanceEvidence, Tenure, Promotion,
    AdjustmentProposal, ApprovalEvent, ExchangeRate,
    RoleComparabilityRationale, GroundTruthRecord
)


def parse_dates_in_records(records: list) -> list:
    """Converts ISO date and datetime strings into Python date/datetime objects for SQLAlchemy."""
    converted = []
    for r in records:
        new_r = {}
        for k, v in r.items():
            if isinstance(v, str):
                if len(v) == 10 and v[4] == '-' and v[7] == '-':
                    try:
                        new_r[k] = datetime.strptime(v, "%Y-%m-%d").date()
                        continue
                    except ValueError:
                        pass
                elif len(v) >= 19 and v[10] in ('T', ' '):
                    try:
                        clean_v = v[:19].replace('T', ' ')
                        new_r[k] = datetime.strptime(clean_v, "%Y-%m-%d %H:%M:%S")
                        continue
                    except ValueError:
                        pass
            new_r[k] = v
        converted.append(new_r)
    return converted


def load_dataset_into_db(data: dict):
    """Inserts generated in-memory records into database inside a transaction."""
    init_db()
    session = SessionLocal()
    try:
        # Clear existing records in reverse dependency order
        session.query(GroundTruthRecord).delete()
        session.query(RoleComparabilityRationale).delete()
        session.query(ExchangeRate).delete()
        session.query(ApprovalEvent).delete()
        session.query(AdjustmentProposal).delete()
        session.query(Promotion).delete()
        session.query(Tenure).delete()
        session.query(PerformanceEvidence).delete()
        session.query(SalaryRecord).delete()
        session.query(Employee).delete()
        session.query(CompensationBand).delete()
        session.query(Level).delete()
        session.query(Role).delete()
        session.query(Location).delete()
        session.commit()

        # Insert master tables
        session.bulk_insert_mappings(Location, parse_dates_in_records(data["locations"]))
        session.bulk_insert_mappings(Role, parse_dates_in_records(data["roles"]))
        session.bulk_insert_mappings(Level, parse_dates_in_records(data["levels"]))
        session.bulk_insert_mappings(ExchangeRate, parse_dates_in_records(data["exchange_rates"]))
        session.bulk_insert_mappings(RoleComparabilityRationale, parse_dates_in_records(data["role_comparability_rationales"]))
        session.commit()

        # Insert bands
        session.bulk_insert_mappings(CompensationBand, parse_dates_in_records(data["compensation_bands"]))
        session.commit()

        # Insert employees
        session.bulk_insert_mappings(Employee, parse_dates_in_records(data["employees"]))
        session.commit()

        # Insert employee child tables
        sal_keys = {"salary_id", "employee_id", "base_salary", "currency", "fte", "pay_frequency", "normalized_salary", "normalized_currency", "effective_date", "end_date", "change_reason", "benchmark_band_id", "created_at"}
        cleaned_salaries = [{k: v for k, v in r.items() if k in sal_keys} for r in data["salary_records"]]
        session.bulk_insert_mappings(SalaryRecord, parse_dates_in_records(cleaned_salaries))

        session.bulk_insert_mappings(PerformanceEvidence, parse_dates_in_records(data["performance_evidence"]))
        session.bulk_insert_mappings(Tenure, parse_dates_in_records(data["tenure_records"]))
        session.bulk_insert_mappings(Promotion, parse_dates_in_records(data["promotions"]))
        session.commit()

        # Insert proposals and approval events
        session.bulk_insert_mappings(AdjustmentProposal, parse_dates_in_records(data["adjustment_proposals"]))
        session.bulk_insert_mappings(ApprovalEvent, parse_dates_in_records(data["approval_events"]))
        session.commit()

        # Insert ground truth records
        session.bulk_insert_mappings(GroundTruthRecord, parse_dates_in_records(data["ground_truth_records"]))
        session.commit()

        print("Database successfully populated with generated records.")
    except Exception as e:
        session.rollback()
        print(f"Error loading data into database: {e}", file=sys.stderr)
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic data for Compensation Equity System.")
    parser.add_argument("--scale", choices=["starter", "full"], default="starter", help="Dataset scale")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Random seed for reproducibility")
    parser.add_argument("--load-db", action="store_true", default=True, help="Load generated data into database")
    parser.add_argument("--no-load-db", dest="load_db", action="store_false", help="Skip loading into database")
    args = parser.parse_args()

    print(f"Starting synthetic data generation (Scale: {args.scale}, Seed: {args.seed})...")
    generator = SyntheticDataGenerator(seed=args.seed, scale=args.scale)
    data = generator.generate_all()

    target_dir = FULL_DATA_DIR if args.scale == "full" else STARTER_DATA_DIR
    print(f"Exporting datasets to {target_dir}...")
    manifest = DatasetExporter.export_all(data, target_dir)

    print("\nGeneration and Export Summary:")
    for tbl, count in manifest["row_counts"].items():
        print(f"  - {tbl:<30}: {count:>6} rows")

    if args.load_db:
        print("\nLoading dataset into database...")
        load_dataset_into_db(data)

    print(f"\nCompleted successfully! Files saved to: {target_dir}")


if __name__ == "__main__":
    main()
