"""
Reproducibility Verification Engine.
Runs the generator twice with the identical seed and verifies bit-for-bit equality
across row counts, deterministic IDs, derived calculations, and SHA-256 hashes.
"""
import hashlib
import json
from typing import Dict, Any, Tuple
from src.generator.synthetic_generator import SyntheticDataGenerator


class ReproducibilityVerifier:
    """Verifies that synthetic data generation is 100% deterministic and reproducible."""

    @classmethod
    def verify(cls, seed: int = 20261022, scale: str = "starter") -> Dict[str, Any]:
        """
        Executes two independent generation runs with the same seed and compares all outputs.
        """
        # Run 1
        gen1 = SyntheticDataGenerator(seed=seed, scale=scale)
        data1 = gen1.generate_all()

        # Run 2
        gen2 = SyntheticDataGenerator(seed=seed, scale=scale)
        data2 = gen2.generate_all()

        results = {
            "seed": seed,
            "scale": scale,
            "is_reproducible": True,
            "tables_checked": len(data1),
            "table_results": {},
            "mismatches": []
        }

        for table_name in data1.keys():
            rows1 = data1[table_name]
            rows2 = data2[table_name]

            count1 = len(rows1)
            count2 = len(rows2)

            # Compare row counts
            if count1 != count2:
                results["is_reproducible"] = False
                results["mismatches"].append(f"Row count mismatch in '{table_name}': {count1} vs {count2}")

            # Compute content hashes
            h1 = cls._hash_records(rows1)
            h2 = cls._hash_records(rows2)

            is_match = (h1 == h2) and (count1 == count2)
            if not is_match:
                results["is_reproducible"] = False
                results["mismatches"].append(f"Content hash mismatch in '{table_name}': {h1} vs {h2}")

            results["table_results"][table_name] = {
                "rows_run1": count1,
                "rows_run2": count2,
                "sha256_run1": h1,
                "sha256_run2": h2,
                "is_match": is_match
            }

        return results

    @staticmethod
    def _hash_records(records: list) -> str:
        """Computes deterministic SHA-256 hash of sorted JSON-serialized records."""
        serialized = json.dumps(records, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
