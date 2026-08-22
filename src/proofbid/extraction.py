"""Deterministic, evidence-bound requirement extraction baseline."""

from __future__ import annotations

import hashlib
import re
from typing import Iterable

from .contracts import (
    DocumentType,
    EvidenceRef,
    ExtractionResult,
    Requirement,
    RequirementCategory,
    SourceDocument,
)


_CATEGORY_TERMS: tuple[tuple[RequirementCategory, tuple[str, ...]], ...] = (
    (RequirementCategory.QUALIFICATION, ("资格", "资质", "证照", "投标人要求", "供应商要求")),
    (RequirementCategory.TECHNICAL, ("技术", "参数", "性能", "规格", "功能", "服务要求")),
    (RequirementCategory.COMMERCIAL, ("商务", "付款", "交付", "售后", "质保", "业绩")),
    (RequirementCategory.PRICING, ("报价", "价格", "预算", "限价", "费用", "税率")),
    (RequirementCategory.CONTRACT, ("合同", "违约", "验收", "履约", "保密", "争议")),
    (RequirementCategory.SUBMISSION, ("递交", "提交", "投标文件", "截止", "开标", "封装", "签章")),
)

_MANDATORY_TERMS = ("必须", "应当", "应", "须", "不得", "不允许", "不低于", "不少于", "不超过")
_REQUIREMENT_TERMS = _MANDATORY_TERMS + ("要求", "提供", "具备", "具有", "提交", "递交", "报价")
_BULLET_RE = re.compile(
    r"^\s*(?:[-*+]\s+|\d+(?:\.\d+)*[.、)]\s*|[（(][一二三四五六七八九十\d]+[)）]\s*|[一二三四五六七八九十]+、\s*)"
)
_MARKDOWN_HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")
_PLAIN_HEADING_RE = re.compile(
    r"^\s*(?:第?[一二三四五六七八九十\d]+[章节部分、.]?\s*)?[^。；]{0,30}"
    r"(?:要求|须知|条款|标准|说明|清单|参数|报价|合同|递交|提交)\s*[:：]?\s*$"
)
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _classify(text: str, fallback: RequirementCategory = RequirementCategory.UNKNOWN) -> RequirementCategory:
    for category, terms in _CATEGORY_TERMS:
        if any(term in text for term in terms):
            return category
    return fallback


def _heading(line: str) -> str | None:
    match = _MARKDOWN_HEADING_RE.match(line)
    if match:
        return match.group(1).strip()
    stripped = line.strip()
    if len(stripped) <= 48 and _PLAIN_HEADING_RE.match(stripped):
        return stripped.rstrip(":：").strip()
    return None


def _clean_title(text: str) -> str:
    cleaned = _BULLET_RE.sub("", text).strip().strip("| ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned if len(cleaned) <= 64 else f"{cleaned[:61]}..."


def _is_candidate(line: str, current_category: RequirementCategory) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith(">") or _TABLE_SEPARATOR_RE.match(stripped):
        return False
    if _BULLET_RE.match(line):
        return True
    if any(term in stripped for term in _REQUIREMENT_TERMS):
        return True
    if current_category is not RequirementCategory.UNKNOWN and stripped.startswith("|"):
        return True
    return False


def _extract_document(document: SourceDocument) -> ExtractionResult:
    if document.document_type not in (DocumentType.MARKDOWN, DocumentType.TEXT):
        return ExtractionResult(requirements=(), evidence=())

    payload = document.path.read_bytes()
    current_hash = hashlib.sha256(payload).hexdigest()
    if current_hash != document.source_hash:
        raise ValueError(f"Source changed after intake: {document.relative_path}")
    text = payload.decode("utf-8-sig")

    requirements: list[Requirement] = []
    evidence: list[EvidenceRef] = []
    current_category = RequirementCategory.UNKNOWN
    current_heading = ""

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        heading = _heading(raw_line)
        if heading is not None:
            current_heading = heading
            current_category = _classify(heading)
            continue
        if not _is_candidate(raw_line, current_category):
            continue

        excerpt = raw_line.strip()
        category = (
            current_category
            if current_category is not RequirementCategory.UNKNOWN
            else _classify(excerpt)
        )
        locator = f"line:{line_number}"
        evidence_id = _stable_id("ev", document.source_hash, locator, excerpt)
        confidence = 0.98 if category is not RequirementCategory.UNKNOWN else 0.70
        ref = EvidenceRef(
            evidence_id=evidence_id,
            source_document_id=document.document_id,
            source_path=document.relative_path,
            source_hash=document.source_hash,
            locator=locator,
            excerpt=excerpt,
            extracted_value=_BULLET_RE.sub("", excerpt).strip(),
            confidence=confidence,
        )
        title = _clean_title(excerpt)
        if current_heading and title.casefold() != current_heading.casefold():
            title = f"{current_heading}：{title}"
            if len(title) > 96:
                title = f"{title[:93]}..."
        requirement = Requirement(
            req_id=_stable_id("req", document.source_hash, locator, excerpt),
            title=title,
            category=category,
            mandatory=(
                any(term in excerpt for term in _MANDATORY_TERMS)
                or bool(
                    re.search(
                        r"(?:截止|限期|\d+(?:\.\d+)?\s*(?:个\s*)?(?:自然日|工作日|日|天|小时)内)",
                        excerpt,
                    )
                )
            ),
            text=_BULLET_RE.sub("", excerpt).strip(),
            evidence_ids=(evidence_id,),
            source_locator=locator,
            source_hash=document.source_hash,
            attributes={"section": current_heading or None},
        )
        evidence.append(ref)
        requirements.append(requirement)

    return ExtractionResult(requirements=tuple(requirements), evidence=tuple(evidence))


def extract_requirements(documents: Iterable[SourceDocument]) -> ExtractionResult:
    """Extract requirement candidates from Markdown/text with immutable evidence."""

    requirements: list[Requirement] = []
    evidence: list[EvidenceRef] = []
    seen_requirements: set[str] = set()
    seen_evidence: set[str] = set()
    for document in documents:
        result = _extract_document(document)
        for requirement in result.requirements:
            if requirement.req_id not in seen_requirements:
                requirements.append(requirement)
                seen_requirements.add(requirement.req_id)
        for ref in result.evidence:
            if ref.evidence_id not in seen_evidence:
                evidence.append(ref)
                seen_evidence.add(ref.evidence_id)
    return ExtractionResult(requirements=tuple(requirements), evidence=tuple(evidence))


__all__ = ["extract_requirements"]
