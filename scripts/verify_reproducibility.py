"""
CLI Script to demonstrate 100% reproducibility of synthetic data generator.
Executes two independent generation runs and asserts equality across rows and SHA-256 hashes.
"""
import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RANDOM_SEED
from src.validation.reproducibility import ReproducibilityVerifier


def main():
    parser = argparse.ArgumentParser(description="Verify Synthetic Generator Reproducibility.")
    parser.add_argument("--scale", choices=["starter", "full"], default="starter")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()

    print(f"Executing double-run reproducibility verification (Scale: {args.scale}, Seed: {args.seed})...")
    results = ReproducibilityVerifier.verify(seed=args.seed, scale=args.scale)

    print("\n--- Reproducibility Comparison Report ---")
    print(f"{'Table Name':<32} | {'Run 1 Rows':<10} | {'Run 2 Rows':<10} | {'Hashes Match':<12}")
    print("-" * 72)

    for tbl, res in results["table_results"].items():
        match_str = "MATCH" if res["is_match"] else "MISMATCH"
        print(f"{tbl:<32} | {res['rows_run1']:<10} | {res['rows_run2']:<10} | {match_str:<12}")

    print("-" * 72)
    if results["is_reproducible"]:
        print("\nSUCCESS: All tables, deterministic IDs, and row contents are 100% reproducible!")
        sys.exit(0)
    else:
        print("\nFAILURE: Reproducibility check failed. Mismatches detected:", file=sys.stderr)
        for m in results["mismatches"]:
            print(f"  - {m}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
