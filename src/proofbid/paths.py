"""Resolve repository assets across source checkouts, installed CLIs, and containers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


def project_root(
    environ: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
) -> Path:
    env = os.environ if environ is None else environ
    configured = env.get("PROOFBID_PROJECT_ROOT")
    if configured:
        candidate = Path(configured).expanduser().resolve()
        if not (candidate / "examples").is_dir():
            raise RuntimeError("PROOFBID_PROJECT_ROOT does not contain examples/")
        return candidate

    working = Path.cwd().resolve() if cwd is None else Path(cwd).expanduser().resolve()
    module_checkout = Path(__file__).resolve().parents[2]
    candidates = (working, *working.parents, module_checkout)
    for candidate in candidates:
        if (candidate / "pyproject.toml").is_file() and (candidate / "examples").is_dir():
            return candidate
    raise RuntimeError(
        "ProofBid project assets were not found; run from a checkout or set PROOFBID_PROJECT_ROOT"
    )


__all__ = ["project_root"]
