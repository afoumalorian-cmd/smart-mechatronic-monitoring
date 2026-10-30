"""Validate a completed RAW file and import its valid measurements."""

import argparse
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from pipeline_state import file_sha256, load_state, save_state

from import_sqlite import import_file
from validate_telemetry import validate_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", type=Path)
    source_group.add_argument("--resume", type=Path)
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    previous_state = None

    if args.resume is not None:
        try:
            previous_state = load_state(args.resume)
        except (OSError, ValueError) as exc:
            parser.error(f"Cannot resume pipeline: {exc}")

        input_path = Path(previous_state["source_file"]).resolve()
        default_database = Path(previous_state["database"]).resolve()
    else:
        input_path = args.input.resolve()
        default_database = (
            project_root / "data" / "local" / "telemetry.sqlite3"
        )

    database_path = (
        args.database.resolve()
        if args.database is not None
        else default_database
    )

    if not input_path.is_file():
        parser.error(f"Input file not found: {input_path}")

    if database_path == input_path:
        parser.error("The database and RAW input paths must be different.")

    run_id = uuid4().hex
    state_path = project_root / "data" / "pipeline" / f"{run_id}.json"
    state = {
        "run_id": run_id,
        "source_file": str(input_path),
        "database": str(database_path),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "started",
    }

    if previous_state is not None:
        state["resumed_from_run_id"] = previous_state["run_id"]
        state["resumed_from_state_file"] = str(args.resume.resolve())

    try:
        save_state(state_path, state)
        print(f"Pipeline state: {state_path}", flush=True)

        state["source_sha256"] = file_sha256(input_path)
        save_state(state_path, state)

        if (
            previous_state is not None
            and state["source_sha256"] != previous_state["source_sha256"]
        ):
            raise ValueError("RAW source changed since the previous run.")

        output_dir, validation = validate_file(input_path)

        # Detect source changes before importing any measurements.
        if file_sha256(input_path) != state["source_sha256"]:
            raise ValueError("RAW source changed during validation.")

        state.update({
            "status": "validated",
            "validation_directory": str(output_dir),
            "validation_counts": validation["counts"],
        })
        save_state(state_path, state)

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

        state.update({
            **summary,
            "status": (
                "completed_with_rejections"
                if validation["counts"]["invalid"]
                else "completed"
            ),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        })
        save_state(state_path, state)

    except (OSError, ValueError, sqlite3.Error, KeyboardInterrupt) as exc:
        state.update({
            "status": (
                "interrupted"
                if isinstance(exc, KeyboardInterrupt)
                else "failed"
            ),
            "error": str(exc) or type(exc).__name__,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        })

        try:
            save_state(state_path, state)
        except OSError as state_error:
            print(f"Could not save pipeline state: {state_error}")

        print(f"Pipeline failed: {state['error']}")
        return 130 if isinstance(exc, KeyboardInterrupt) else 1

    print(json.dumps(summary, indent=2, allow_nan=False))
    return 1 if validation["counts"]["invalid"] else 0


if __name__ == "__main__":
    raise SystemExit(main())