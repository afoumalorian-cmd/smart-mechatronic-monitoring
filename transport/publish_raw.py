"""Publish local RAW telemetry with explicit checkpoint recovery."""

import argparse
import json
import os
import sys
from pathlib import Path

from transport.local_publisher import LocalPublisher
from transport.publication_journal import (
    load_journal,
    new_journal,
    save_journal,
)
from transport.publication_lock import publication_lock
from transport.publication_recovery import restore_checkpoint
from transport.publication_step import process_next


def run(input_path, journal_path, *, follow=False, replay=False, limit=0):
    """Publish RAW records, retaining progress across explicit restarts."""
    state = None
    processed_this_run = 0
    error = None
    exit_code = 0

    try:
        lock_path = journal_path.with_name(journal_path.name + ".lock")
        reports_path = journal_path.with_name(
            journal_path.name + ".rejections"
        )

        if input_path in (journal_path, lock_path):
            raise ValueError("RAW must differ from journal and lock paths.")

        if input_path.is_relative_to(reports_path):
            raise ValueError("RAW must be outside the rejection-report directory.")

        for target in (journal_path, lock_path):
            if target.exists() and os.path.samefile(input_path, target):
                raise ValueError("RAW must not alias the journal or lock file.")

        with publication_lock(journal_path):
            if replay and journal_path.exists():
                raise ValueError("Replay requires a new journal path.")

            with input_path.open("rb", buffering=0) as source:
                if journal_path.exists():
                    state = load_journal(journal_path)

                    if Path(state["source_file"]) != input_path:
                        raise ValueError("Journal belongs to another RAW path.")
                else:
                    state = new_journal(input_path, source)
                    save_journal(journal_path, state)

                # Verify recovery before opening the MQTT connection.
                restore_checkpoint(source, state)

                print(f"RAW source: {input_path}", flush=True)
                print(f"Publication journal: {journal_path}", flush=True)
                print(
                    f"Starting after {state['processed_lines']} processed lines.",
                    flush=True,
                )

                with LocalPublisher() as publisher:
                    while True:
                        publisher.poll()

                        candidate = process_next(
                            source,
                            state,
                            journal_path,
                            publisher.publish,
                            completed=not follow,
                        )

                        if candidate is None:
                            if follow:
                                continue
                            break

                        state = candidate
                        processed_this_run += 1

                        print(json.dumps({
                            "processed_this_run": processed_this_run,
                            "next_offset": state["next_offset"],
                            "counts": state["counts"],
                        }), flush=True)

                        if limit and processed_this_run >= limit:
                            break

    except KeyboardInterrupt:
        error = "Interrupted; recover from the persisted publication journal."
        exit_code = 130
    except Exception as exc:
        error = str(exc)
        exit_code = 1

    print(json.dumps({
        "source_file": str(input_path),
        "journal": str(journal_path),
        "processed_this_run": processed_this_run,
        "counts": state["counts"] if state is not None else None,
        "error": error,
        "storage_confirmation": "Broker PUBACK is not SQLite confirmation.",
    }, indent=2))

    return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument(
        "--follow",
        action="store_true",
        help="Wait for complete lines appended to an active RAW file.",
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Replay from the beginning using a new journal path.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum lines processed this run, including rejections; 0 means no limit.",
    )
    args = parser.parse_args()

    input_path = args.input.resolve()
    journal_path = args.journal.resolve()

    if not input_path.is_file():
        parser.error(f"RAW input not found: {input_path}")
    if args.limit < 0:
        parser.error("--limit must be non-negative.")

    return run(
        input_path,
        journal_path,
        follow=args.follow,
        replay=args.replay,
        limit=args.limit,
    )


if __name__ == "__main__":
    sys.exit(main())