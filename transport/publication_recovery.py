"""Verify a RAW checkpoint and reconstruct sequence tracking."""

import os
from pathlib import Path

from transport.publication_journal import OUTCOMES, validate_journal
from transport.raw_source import prefix_sha256, read_raw_line
from transport.raw_validation import classify_raw_line


def verify_source_identity(source, state):
    """Check that the opened file and current path match the journal."""
    opened = os.fstat(source.fileno())
    current = Path(state["source_file"]).stat()
    expected = tuple(state["source_identity"])

    if (
        (opened.st_dev, opened.st_ino) != expected
        or (current.st_dev, current.st_ino) != expected
    ):
        raise ValueError("RAW source identity changed.")

    if opened.st_size < state["next_offset"]:
        raise ValueError("RAW source is shorter than the checkpoint.")


def restore_checkpoint(source, state):
    """Verify processed lines and return reconstructed sequence tracking.

    On success, position the reader at next_offset.
    On failure, restore its original position.
    The source must be opened in binary mode without buffering.
    The caller must hold the publication journal lock.

    These checks do not lock the RAW source against concurrent changes.
    """
    validate_journal(state)
    original_position = source.tell()

    try:
        verify_source_identity(source, state)

        if prefix_sha256(source, state["next_offset"]) != state["prefix_sha256"]:
            raise ValueError("Processed RAW prefix changed.")

        source.seek(0)
        last_sequences = {}
        counts = {outcome: 0 for outcome in OUTCOMES}

        for _ in range(state["processed_lines"]):
            raw_line = read_raw_line(source, completed=True)

            if raw_line is None:
                raise ValueError("RAW contains fewer lines than the checkpoint.")

            if source.tell() > state["next_offset"]:
                raise ValueError("Checkpoint offset does not match line boundaries.")

            _, category, _ = classify_raw_line(raw_line, last_sequences)
            outcome = "broker_confirmed" if category == "valid" else category
            counts[outcome] += 1

        if source.tell() != state["next_offset"]:
            raise ValueError("Checkpoint line count does not match its offset.")

        if counts != state["counts"]:
            raise ValueError("RAW classifications do not match checkpoint counters.")

        # Recheck after reconstruction before trusting the recovered cursor.
        verify_source_identity(source, state)

        if prefix_sha256(source, state["next_offset"]) != state["prefix_sha256"]:
            raise ValueError("Processed RAW prefix changed during recovery.")

        return last_sequences

    except BaseException:
        source.seek(original_position)
        raise