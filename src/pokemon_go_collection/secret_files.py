"""Secrets kept one per file, readable by the user alone."""

import os


def read_secret(file_path):
    """Return the secret held in `file_path`, or None when it is not set."""
    if not file_path.exists():
        return None
    return file_path.read_text(encoding="utf-8").strip() or None


def write_secret(file_path, value):
    file_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    file_descriptor = os.open(file_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(file_descriptor, "w", encoding="utf-8") as file:
        file.write(value)
    # A file created before keeps its own mode through `os.open`.
    os.chmod(file_path, 0o600)
