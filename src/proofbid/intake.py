"""Safe, deterministic intake for the local ProofBid workspace."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Iterable

from .contracts import DocumentType, SourceDocument


DEFAULT_MAX_FILE_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_FILES = 128

_TYPE_BY_SUFFIX = {
    ".md": DocumentType.MARKDOWN,
    ".txt": DocumentType.TEXT,
    ".json": DocumentType.JSON,
    ".csv": DocumentType.CSV,
}


class IntakeError(ValueError):
    """Raised when an input violates the untrusted-document boundary."""


class PathBoundaryError(IntakeError):
    pass


class UnsupportedDocumentError(IntakeError):
    pass


class OversizedDocumentError(IntakeError):
    pass


def _stable_id(relative_path: str, source_hash: str) -> str:
    payload = f"{relative_path}\0{source_hash}".encode("utf-8")
    return f"doc-{hashlib.sha256(payload).hexdigest()[:16]}"


def _assert_within_root(path: Path, root: Path) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as exc:
        raise PathBoundaryError(f"Input path cannot be resolved safely: {path}") from exc
    if not resolved.is_relative_to(root):
        raise PathBoundaryError(f"Input escapes workspace boundary: {path}")
    return resolved


def _candidate_files(root: Path, paths: Iterable[str | Path] | None) -> list[Path]:
    if paths is None:
        candidates = list(root.rglob("*"))
    else:
        candidates = []
        for raw in paths:
            lexical = Path(raw)
            if not lexical.is_absolute() and ".." in lexical.parts:
                raise PathBoundaryError(f"Parent traversal is not allowed: {raw}")
            candidate = lexical if lexical.is_absolute() else root / lexical
            resolved = _assert_within_root(candidate, root)
            if candidate.is_symlink() or resolved.is_symlink():
                raise PathBoundaryError(f"Symbolic links are not accepted: {raw}")
            if resolved.is_dir():
                candidates.extend(resolved.rglob("*"))
            else:
                candidates.append(resolved)

    files: list[Path] = []
    for candidate in candidates:
        if candidate.is_symlink():
            raise PathBoundaryError(f"Symbolic links are not accepted: {candidate}")
        resolved = _assert_within_root(candidate, root)
        if resolved.is_dir():
            continue
        if not resolved.is_file():
            raise IntakeError(f"Only regular files are accepted: {candidate}")
        files.append(resolved)
    return sorted(set(files), key=lambda item: item.relative_to(root).as_posix())


def _validate_payload(payload: bytes, document_type: DocumentType, relative_path: str) -> None:
    if b"\x00" in payload:
        raise UnsupportedDocumentError(f"Binary content is not accepted: {relative_path}")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UnsupportedDocumentError(f"Input must be UTF-8 text: {relative_path}") from exc

    try:
        if document_type is DocumentType.JSON:
            json.loads(text)
        elif document_type is DocumentType.CSV:
            list(csv.reader(io.StringIO(text)))
    except (json.JSONDecodeError, csv.Error) as exc:
        raise UnsupportedDocumentError(f"Malformed {document_type.value}: {relative_path}") from exc


def scan_workspace(
    workspace: str | Path,
    paths: Iterable[str | Path] | None = None,
    *,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_files: int = DEFAULT_MAX_FILES,
) -> tuple[SourceDocument, ...]:
    """Scan an isolated input workspace and reject unsafe or unknown files.

    Only UTF-8 ``.md``, ``.txt``, ``.json`` and ``.csv`` files are accepted.
    Both explicit paths and discovered symlinks are rejected when they could
    bypass the resolved workspace boundary.
    """

    if max_file_bytes <= 0 or max_files <= 0:
        raise ValueError("max_file_bytes and max_files must be positive")
    root = Path(workspace).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise IntakeError(f"Workspace is not a directory: {workspace}")

    files = _candidate_files(root, paths)
    if len(files) > max_files:
        raise IntakeError(f"Workspace has {len(files)} files; limit is {max_files}")

    documents: list[SourceDocument] = []
    for path in files:
        relative_path = path.relative_to(root).as_posix()
        document_type = _TYPE_BY_SUFFIX.get(path.suffix.casefold())
        if document_type is None:
            raise UnsupportedDocumentError(f"Unsupported document type: {relative_path}")

        before = path.stat()
        if before.st_size > max_file_bytes:
            raise OversizedDocumentError(
                f"Document exceeds {max_file_bytes} bytes: {relative_path} ({before.st_size})"
            )
        payload = path.read_bytes()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise IntakeError(f"Document changed during intake: {relative_path}")
        if len(payload) != before.st_size:
            raise IntakeError(f"Document size changed during intake: {relative_path}")

        _validate_payload(payload, document_type, relative_path)
        source_hash = hashlib.sha256(payload).hexdigest()
        documents.append(
            SourceDocument(
                document_id=_stable_id(relative_path, source_hash),
                relative_path=relative_path,
                path=path,
                document_type=document_type,
                source_hash=source_hash,
                size_bytes=len(payload),
            )
        )
    return tuple(documents)


__all__ = [
    "DEFAULT_MAX_FILE_BYTES",
    "DEFAULT_MAX_FILES",
    "IntakeError",
    "OversizedDocumentError",
    "PathBoundaryError",
    "UnsupportedDocumentError",
    "scan_workspace",
]
