"""Read complete RAW JSONL lines from a binary source file."""


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