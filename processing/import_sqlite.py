"""Import validated telemetry into SQLite without duplicating measurements."""

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from validate_telemetry import reject_constant, validate_record
from measurement_record import measurement_parts
from sqlite_schema import initialize_database


def import_records(connection, input_path):
    """Import one file atomically and return its execution summary."""
    import_id = uuid4().hex
    imported_at = datetime.now(timezone.utc).isoformat()

    counts = {
        "records_read": 0,
        "records_inserted": 0,
        "duplicates_skipped": 0,
    }

    # The context manager commits on success and rolls back on failure.
    # A failed import leaves no new measurements or import history row.
    with connection:
        connection.execute(
            """
            INSERT INTO import_runs (
                import_id, imported_at_utc, source_file,
                records_read, records_inserted, duplicates_skipped
            )
            VALUES (?, ?, ?, 0, 0, 0)
            """,
            (import_id, imported_at, str(input_path)),
        )

        # Open the source in read-only mode; never modify validated files.
        with input_path.open("r", encoding="utf-8") as source:
            for line_number, line in enumerate(source, start=1):
                counts["records_read"] += 1

                try:
                    record = json.loads(
                        line, parse_constant=reject_constant
                    )
                    category, issues = validate_record(record)
                except ValueError as exc:
                    raise ValueError(
                        f"Line {line_number}: invalid JSON: {exc}"
                    ) from exc

                # A file named valid.jsonl must still pass validation.
                if category != "valid":
                    details = "; ".join(issues) or category
                    raise ValueError(
                        f"Line {line_number}: expected valid telemetry: "
                        f"{details}"
                    )

                key, values = measurement_parts(record)

                existing = connection.execute(
                    """
                    SELECT received_at_utc, uptime_ms, sensor, status,
                           temperature_c, humidity_pct
                    FROM measurements
                    WHERE session_id = ? AND device_id = ? AND sequence = ?
                    """,
                    key,
                ).fetchone()

                if existing is not None:
                    # Only identical measurements count as duplicates.
                    if existing != values:
                        raise ValueError(
                            f"Line {line_number}: conflicting measurement "
                            f"for key {key!r}."
                        )

                    counts["duplicates_skipped"] += 1
                    continue

                # Placeholders bind values safely without building SQL text.
                connection.execute(
                    """
                    INSERT INTO measurements (
                        import_id, source_line,
                        session_id, device_id, sequence,
                        received_at_utc, uptime_ms, sensor, status,
                        temperature_c, humidity_pct
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (import_id, line_number, *key, *values),
                )
                counts["records_inserted"] += 1

        if counts["records_read"] == 0:
            raise ValueError("The input file is empty.")

        # Finalize the history row inside the same transaction.
        connection.execute(
            """
            UPDATE import_runs
            SET records_read = ?,
                records_inserted = ?,
                duplicates_skipped = ?
            WHERE import_id = ?
            """,
            (
                counts["records_read"],
                counts["records_inserted"],
                counts["duplicates_skipped"],
                import_id,
            ),
        )

    # This summary is returned only after the transaction commits.
    return {
        "import_id": import_id,
        "imported_at_utc": imported_at,
        "source_file": str(input_path),
        **counts,
    }


def import_file(input_path, database_path):
    """Open SQLite, import one file, and always close the connection."""
    input_path = Path(input_path).resolve()
    database_path = Path(database_path).resolve()

    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if database_path == input_path:
        raise ValueError("The database and input paths must be different.")

    connection = None

    try:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database_path)
        initialize_database(connection)

        return import_records(connection, input_path)

    finally:
        # Transaction handling does not close the SQLite connection.
        if connection is not None:
            connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Validated JSONL file to import.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        help="SQLite database; defaults to data/local/telemetry.sqlite3.",
    )
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

    # Protect the source from accidentally being used as the database.
    if database_path == input_path:
        parser.error("The database and input paths must be different.")

    try:
        summary = import_file(input_path, database_path)

    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Import failed: {exc}")
        return 1

    print(json.dumps(
        {"database": str(database_path), **summary},
        indent=2,
        allow_nan=False,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())