"""Validate a completed RAW file and import its valid measurements."""

import argparse
import json
import sqlite3
from pathlib import Path

from import_sqlite import import_file
from validate_telemetry import validate_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    input_path = args.input.resolve()
    database_path = (
        args.database.resolve()
        if args.database is not None
        else project_root / "data" / "local" / "telemetry.sqlite3"
    )

    if not input_path.is_file():
        parser.error(f"Input file not found: {input_path}")

    if database_path == input_path:
        parser.error("The database and RAW input paths must be different.")

    try:
        output_dir, validation = validate_file(input_path)

        # Import only valid measurements; retain all validation outputs.
        import_summary = None
        if validation["counts"]["valid"] > 0:
            import_summary = import_file(
                output_dir / "valid.jsonl", database_path
            )

        summary = {
            "source_file": str(input_path),
            "validation_directory": str(output_dir),
            "database": str(database_path),
            "validation_counts": validation["counts"],
            "import": import_summary,
            "import_skipped": import_summary is None,
        }

    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Pipeline failed: {exc}")
        return 1

    print(json.dumps(summary, indent=2, allow_nan=False))
    return 1 if validation["counts"]["invalid"] else 0


if __name__ == "__main__":
    raise SystemExit(main())