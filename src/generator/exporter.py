"""
Export Service for Synthetic Datasets.
Exports relational data to CSV, JSON, reproducible SQL seed scripts,
and produces isolated ground_truth.csv / ground_truth.json.
"""
from pathlib import Path
import json
import hashlib
from typing import Dict, List, Any
import pandas as pd


class DatasetExporter:
    """Exports generated in-memory datasets into CSV, JSON, and SQL formats."""

    @staticmethod
    def export_all(data: Dict[str, List[Dict[str, Any]]], output_dir: Path) -> Dict[str, Any]:
        """
        Exports all tables into CSV, JSON, and SQL seed script.
        Calculates SHA-256 checksums and returns manifest summary.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"files": {}, "row_counts": {}}

        # Export CSVs & JSONs
        for table_name, records in data.items():
            if not records:
                continue

            df = pd.DataFrame(records)
            row_count = len(df)
            manifest["row_counts"][table_name] = row_count

            # CSV
            csv_path = output_dir / f"{table_name}.csv"
            df.to_csv(csv_path, index=False)
            csv_sha256 = DatasetExporter._compute_sha256(csv_path)

            # JSON
            json_path = output_dir / f"{table_name}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, default=str)
            json_sha256 = DatasetExporter._compute_sha256(json_path)

            manifest["files"][f"{table_name}.csv"] = {
                "rows": row_count,
                "sha256": csv_sha256,
                "size_bytes": csv_path.stat().st_size
            }
            manifest["files"][f"{table_name}.json"] = {
                "rows": row_count,
                "sha256": json_sha256,
                "size_bytes": json_path.stat().st_size
            }

        # Generate SQL Seed Script
        sql_path = output_dir / "seed_data.sql"
        DatasetExporter._generate_sql_seed(data, sql_path)
        manifest["files"]["seed_data.sql"] = {
            "sha256": DatasetExporter._compute_sha256(sql_path),
            "size_bytes": sql_path.stat().st_size
        }

        # Write manifest.json
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return manifest

    @staticmethod
    def _compute_sha256(filepath: Path) -> str:
        """Computes SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _generate_sql_seed(data: Dict[str, List[Dict[str, Any]]], output_path: Path):
        """Generates reproducible SQL INSERT statements."""
        # Enforce insertion order to respect foreign key constraints
        table_order = [
            "locations", "roles", "levels", "compensation_bands",
            "employees", "salary_records", "performance_evidence",
            "tenure_records", "promotions", "adjustment_proposals",
            "approval_events", "exchange_rates", "role_comparability_rationales",
            "ground_truth_records"
        ]

        with open(output_path, "w", encoding="utf-8") as sql_file:
            sql_file.write("-- Compensation Equity and Disparity Analysis System\n")
            sql_file.write("-- Reproducible Seed Script\n\n")

            for tbl in table_order:
                records = data.get(tbl, [])
                if not records:
                    continue

                sql_file.write(f"-- Table: {tbl} ({len(records)} rows)\n")
                columns = list(records[0].keys())
                col_str = ", ".join(columns)

                for r in records:
                    vals = []
                    for col in columns:
                        v = r.get(col)
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        elif isinstance(v, bool):
                            vals.append("1" if v else "0")
                        else:
                            # Escape single quotes
                            escaped = str(v).replace("'", "''")
                            vals.append(f"'{escaped}'")

                    val_str = ", ".join(vals)
                    sql_file.write(f"INSERT INTO {tbl} ({col_str}) VALUES ({val_str});\n")
                sql_file.write("\n")
