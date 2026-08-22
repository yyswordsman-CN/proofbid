"""Vendor-neutral domain contracts for the ProofBid vertical slice."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


Scalar = str | int | float | bool | None


class DocumentType(str, Enum):
    MARKDOWN = "markdown"
    TEXT = "text"
    JSON = "json"
    CSV = "csv"


class RequirementCategory(str, Enum):
    QUALIFICATION = "qualification"
    TECHNICAL = "technical"
    COMMERCIAL = "commercial"
    PRICING = "pricing"
    CONTRACT = "contract"
    SUBMISSION = "submission"
    UNKNOWN = "unknown"


class MatchStatus(str, Enum):
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKER = "blocker"


@dataclass(frozen=True, slots=True)
class SourceDocument:
    document_id: str
    relative_path: str
    path: Path = field(repr=False, compare=False)
    document_type: DocumentType
    source_hash: str
    size_bytes: int

    @property
    def sha256(self) -> str:
        return self.source_hash


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    evidence_id: str
    source_document_id: str
    source_path: str
    source_hash: str
    locator: str
    excerpt: str
    extracted_value: str | None = None
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not self.source_hash or len(self.source_hash) != 64:
            raise ValueError("EvidenceRef.source_hash must be a SHA-256 hex digest")
        if not self.locator.strip() or not self.excerpt.strip():
            raise ValueError("EvidenceRef requires a locator and non-empty excerpt")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("EvidenceRef.confidence must be between 0 and 1")

    @property
    def quote(self) -> str:
        """Compatibility name used by the evidence-first requirement contract."""
        return self.excerpt


@dataclass(frozen=True, slots=True)
class Requirement:
    req_id: str
    title: str
    category: RequirementCategory
    mandatory: bool
    text: str
    evidence_ids: tuple[str, ...]
    source_locator: str
    source_hash: str
    status: MatchStatus = MatchStatus.UNKNOWN
    attributes: Mapping[str, Scalar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence_ids:
            raise ValueError("Every requirement must reference at least one EvidenceRef")
        if not self.source_locator or len(self.source_hash) != 64:
            raise ValueError("Requirement must retain its source locator and SHA-256")

    @property
    def requirement_id(self) -> str:
        return self.req_id


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    requirements: tuple[Requirement, ...]
    evidence: tuple[EvidenceRef, ...]

    def __post_init__(self) -> None:
        ledger = {item.evidence_id for item in self.evidence}
        missing = {
            evidence_id
            for requirement in self.requirements
            for evidence_id in requirement.evidence_ids
            if evidence_id not in ledger
        }
        if missing:
            raise ValueError(f"Requirements reference missing evidence: {sorted(missing)}")


@dataclass(frozen=True, slots=True)
class BidderFact:
    key: str
    value: Scalar
    evidence_id: str


@dataclass(frozen=True, slots=True)
class BidderProfile:
    source_document_id: str
    source_hash: str
    legal_name: str | None
    facts: tuple[BidderFact, ...]
    evidence: tuple[EvidenceRef, ...]

    def values_for(self, key: str) -> tuple[Scalar, ...]:
        normalized = key.casefold()
        return tuple(fact.value for fact in self.facts if fact.key.casefold() == normalized)


@dataclass(frozen=True, slots=True)
class CatalogItem:
    item_id: str
    name: str | None
    model: str | None
    category: str | None
    unit: str | None
    unit_price: float | None
    currency: str | None
    attributes: Mapping[str, Scalar]
    certifications: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple, repr=False)


@dataclass(frozen=True, slots=True)
class ComplianceMatch:
    match_id: str
    requirement_id: str
    status: MatchStatus
    rationale: str
    candidate_id: str | None
    expected: str | None
    actual: str | None
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MissingItem:
    id: str
    requirement_id: str
    reason_code: str
    description: str
    severity: Severity
    blocks_completion: bool

    def __post_init__(self) -> None:
        if not self.reason_code or not self.reason_code.strip():
            raise ValueError("Missing items require a stable reason_code")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", self.reason_code):
            raise ValueError("Missing-item reason_code must be an uppercase business code")


@dataclass(frozen=True, slots=True)
class Deviation:
    id: str
    requirement_id: str
    expected: str | None
    actual: str | None
    status: MatchStatus
    evidence_ids: tuple[str, ...]
    explanation: str


@dataclass(frozen=True, slots=True)
class BOMLine:
    id: str
    requirement_id: str
    item_id: str | None
    name: str | None
    qty: float | None
    unit: str | None
    unit_price: float | None
    currency: str | None
    status: MatchStatus
    evidence_ids: tuple[str, ...]
    rationale: str


@dataclass(frozen=True, slots=True)
class AnalysisBundle:
    task_id: str
    requirements: tuple[Requirement, ...]
    evidence: tuple[EvidenceRef, ...]
    matches: tuple[ComplianceMatch, ...]
    bom: tuple[BOMLine, ...]
    deviations: tuple[Deviation, ...]
    missing_items: tuple[MissingItem, ...]


@dataclass(frozen=True, slots=True)
class ReadinessDecision:
    """Deterministic package-readiness result.

    ``ready_for_submission`` means the generated preparation package is ready
    for a controlled human submission step.  It never means that ProofBid has
    signed, sent, or submitted a bid.
    """

    ready_for_human_review: bool
    ready_for_submission: bool
    submission_executed: bool
    high_risk_actions_locked: bool
    blocking_reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.submission_executed:
            raise ValueError("ProofBid preparation runs must never execute submission")
        if not self.high_risk_actions_locked:
            raise ValueError("High-risk actions must remain locked")
        if self.ready_for_submission and not self.ready_for_human_review:
            raise ValueError("Submission readiness requires human-review readiness")
        if self.ready_for_submission and self.blocking_reason_codes:
            raise ValueError("A ready package cannot retain blocking reason codes")


def to_primitive(value: Any) -> Any:
    """Convert contracts into JSON-compatible primitives without hiding unknowns."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_primitive(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): to_primitive(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [to_primitive(item) for item in value]
    return value


__all__ = [
    "AnalysisBundle",
    "BOMLine",
    "BidderFact",
    "BidderProfile",
    "CatalogItem",
    "ComplianceMatch",
    "Deviation",
    "DocumentType",
    "EvidenceRef",
    "ExtractionResult",
    "MatchStatus",
    "MissingItem",
    "Requirement",
    "RequirementCategory",
    "ReadinessDecision",
    "Severity",
    "SourceDocument",
    "to_primitive",
]
