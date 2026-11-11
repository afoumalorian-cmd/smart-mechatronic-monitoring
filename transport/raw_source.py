"""Read complete RAW JSONL lines from a binary source file."""
import hashlib


MAX_RAW_LINE_BYTES = 64 * 1024


def read_raw_line(source, *, completed=False):
    """Return one complete line, or None when no complete line is available.

    The source must be a seekable binary file.
    In live mode, an incomplete trailing line is left unread.
    In completed mode, an incomplete trailing line raises ValueError.
    Oversized lines raise ValueError in both modes.

    This function does not establish that the collector has synchronized
    the returned bytes to storage.
    """
    position = source.tell()
    raw_line = source.readline(MAX_RAW_LINE_BYTES + 1)

    if not raw_line:
        return None

    if len(raw_line) > MAX_RAW_LINE_BYTES:
        source.seek(position)
        raise ValueError(
            f"RAW line at byte {position} exceeds "
            f"{MAX_RAW_LINE_BYTES} bytes."
        )

    if not raw_line.endswith(b"\n"):
        source.seek(position)

        if completed:
            raise ValueError(
                f"Incomplete trailing RAW line at byte {position}."
            )

        return None

    return raw_line


def prefix_sha256(source, byte_count):
    """Hash an exact binary prefix without changing the reader position.

    Appended bytes beyond byte_count are excluded.
    A source shorter than the requested prefix raises ValueError.
    """
    if type(byte_count) is not int or byte_count < 0:
        raise ValueError("Prefix length must be a non-negative integer.")

    position = source.tell()
    digest = hashlib.sha256()

    try:
        source.seek(0)
        remaining = byte_count

        while remaining:
            chunk = source.read(min(remaining, 1024 * 1024))

            if not chunk:
                raise ValueError(
                    "RAW source is shorter than the recorded prefix."
                )

            digest.update(chunk)
            remaining -= len(chunk)

        return digest.hexdigest()

    finally:
        source.seek(position)