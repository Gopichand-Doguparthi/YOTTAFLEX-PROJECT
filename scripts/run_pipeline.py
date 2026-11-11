"""
Master Pipeline Runner Script.
Executes the complete end-to-end pipeline:
1. Database migration
2. Synthetic data generation & export
3. Database loading
4. Relational & arithmetic validation checks
5. Ground-truth evaluation benchmarking
"""
import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RANDOM_SEED, STARTER_DATA_DIR, FULL_DATA_DIR
from src.database.session import SessionLocal, init_db
from src.generator.synthetic_generator import SyntheticDataGenerator
from src.generator.exporter import DatasetExporter
from scripts.run_generator import load_dataset_into_db
from src.validation.data_validator import DataValidator
from src.evaluation.evaluator import EvaluationEngine


def main():
    parser = argparse.ArgumentParser(description="Run Full End-to-End Pipeline.")
    parser.add_argument("--scale", choices=["starter", "full"], default="starter")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()

    print(f"==================================================")
    print(f"Starting Compensation Analysis Pipeline")
    print(f"Scale: {args.scale} | Seed: {args.seed}")
    print(f"==================================================")

    # 1. Initialize DB
    print("\n[Step 1/5] Initializing database schema...")
    init_db()

    # 2. Generate Data
    print(f"\n[Step 2/5] Generating synthetic dataset ({args.scale})...")
    generator = SyntheticDataGenerator(seed=args.seed, scale=args.scale)
    data = generator.generate_all()

    # 3. Export Data
    target_dir = FULL_DATA_DIR if args.scale == "full" else STARTER_DATA_DIR
    print(f"\n[Step 3/5] Exporting datasets to {target_dir}...")
    manifest = DatasetExporter.export_all(data, target_dir)
    print(f"Exported {len(manifest['files'])} files.")

    # 4. Load into DB
    print("\n[Step 4/5] Loading data into database...")
    load_dataset_into_db(data)

    # 5. Validate & Evaluate
    print("\n[Step 5/5] Running validation and evaluation...")
    session = SessionLocal()
    try:
        val = DataValidator.run_all_checks(session)
        print(f"Validation Pass Rate: {val['pass_rate_pct']}% ({val['passed_checks']}/{val['total_checks']} checks passed)")

        eval_res = EvaluationEngine.evaluate(session)
        om = eval_res["overall_metrics"]
        print(f"Evaluation Metrics  : Precision={om['precision']*100:.1f}%, Recall={om['recall']*100:.1f}%, F1={om['f1_score']:.4f}")
    finally:
        session.close()

    print("\n==================================================")
    print("Pipeline Execution Completed Successfully!")
    print("==================================================")


if __name__ == "__main__":
    main()
