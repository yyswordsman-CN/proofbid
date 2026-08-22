from __future__ import annotations

from pathlib import Path

import pytest

from proofbid.paths import project_root


def test_project_root_resolves_installed_cli_from_checkout_cwd(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    (checkout / "examples").mkdir(parents=True)
    (checkout / "pyproject.toml").write_text("[project]\nname='proofbid'\n", encoding="utf-8")
    nested = checkout / "apps" / "web"
    nested.mkdir(parents=True)

    assert project_root(environ={}, cwd=nested) == checkout


def test_project_root_rejects_invalid_explicit_root(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="does not contain examples"):
        project_root(environ={"PROOFBID_PROJECT_ROOT": str(tmp_path)})
