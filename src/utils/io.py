# src/utils/io.py
"""
Utility functions for file I/O and reproducibility.

Provides helpers to:
- Read text files safely with UTF-8 encoding.
- Ensure directories exist before writing outputs.
- Generate short SHA-256 digests of text for logging/metadata.
"""

from __future__ import annotations

import hashlib
import os


def read_file(path: str) -> str:
    """
    Read a UTF-8 text file and return its content as a string.

    Args:
        path: Path to the file.

    Returns:
        The file content as a string.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"[ERROR] File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def ensure_dir(path: str) -> None:
    """
    Ensure that a directory exists, creating it if necessary.

    Args:
        path: Path to a directory (or file path — its parent dir will be ensured).

    Notes:
        This is safe to call even if the directory already exists.
    """
    # If the path looks like a file, ensure its parent dir instead.
    dir_path = path if os.path.splitext(path)[1] == "" else os.path.dirname(path)
    os.makedirs(dir_path or ".", exist_ok=True)


def sha256_text(text: str) -> str:
    """
    Return the SHA-256 hex digest of a text string.

    Args:
        text: Input string.

    Returns:
        A 64-character lowercase hex digest, useful for logging/reproducibility.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()