"""Small, dependency-free helpers for non-following atomic local writes."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def secure_staging_path(target: Path) -> Iterator[Path]:
    """Yield an unpredictable, exclusively-created sibling and atomically replace target."""

    descriptor, raw_path = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    os.close(descriptor)
    staging = Path(raw_path)
    try:
        yield staging
        if staging.is_symlink() or not staging.is_file():
            raise ValueError("Atomic staging file was replaced or is not regular")
        os.replace(staging, target)
    finally:
        if staging.is_symlink() or staging.exists():
            staging.unlink()


__all__ = ["secure_staging_path"]
