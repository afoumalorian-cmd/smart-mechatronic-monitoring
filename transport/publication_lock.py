"""Prevent concurrent publishers from sharing a publication journal."""

import os
from contextlib import contextmanager
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl


@contextmanager
def publication_lock(journal_path):
    """Hold a non-blocking OS lock beside the publication journal.

    All publishers using this journal must acquire this lock.
    The lock file remains in place after release.
    """
    journal_path = Path(journal_path).resolve()
    lock_path = journal_path.with_name(journal_path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+b") as lock_file:
        # Windows byte-range locking requires a lockable byte.
        if os.fstat(lock_file.fileno()).st_size == 0:
            lock_file.write(b"\0")
            lock_file.flush()

        lock_file.seek(0)

        try:
            if os.name == "nt":
                msvcrt.locking(
                    lock_file.fileno(), msvcrt.LK_NBLCK, 1
                )
            else:
                fcntl.flock(
                    lock_file.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
        except OSError as exc:
            raise RuntimeError(
                f"Cannot acquire publication lock: {lock_path}. "
                "Another publisher may be using this journal."
            ) from exc

        try:
            yield
        finally:
            lock_file.seek(0)

            if os.name == "nt":
                msvcrt.locking(
                    lock_file.fileno(), msvcrt.LK_UNLCK, 1
                )
            else:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)