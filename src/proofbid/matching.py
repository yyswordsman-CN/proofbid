"""Evidence-aware deterministic matching and explainable BOM baseline."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import replace
from typing import Any, Iterable, Mapping

from .contracts import (
    AnalysisBundle,
    BOMLine,
    BidderFact,
    BidderProfile,
    CatalogItem,
    ComplianceMatch,
    Deviation,
    DocumentType,
    EvidenceRef,
    ExtractionResult,
    MatchStatus,
    MissingItem,
    Requirement,
    RequirementCategory,
    Scalar,
    Severity,
    SourceDocument,
)


_ID_ALIASES = ("item_id", "sku", "product_id", "产品编号", "物料编码", "编号")
_NAME_ALIASES = ("name", "product_name", "产品名称", "商品名称", "名称")
_MODEL_ALIASES = ("model", "型号", "规格型号")
_CATEGORY_ALIASES = ("category", "product_category", "品类", "类别")
_UNIT_ALIASES = ("unit", "单位")
_PRICE_ALIASES = ("unit_price", "price", "单价", "含税单价")
_CURRENCY_ALIASES = ("currency", "币种")
_CERT_ALIASES = ("certifications", "certificates", "认证", "资质", "证书")

_PROFILE_TERMS = (
    "营业执照",
    "法定代表人",
    "授权书",
    "信用",
    "财务",
    "税务",
    "社保",
    "业绩",
    "售后",
    "质保",
    "付款",
    "交付周期",
    "安装计划",
    "测试记录",
    "商务文件",
    "技术文件",
    "报价文件",
    "偏离表",
    "资格证明材料",
)
_ISO_RE = re.compile(r"ISO\s*\d{4,6}(?::\d{4})?", re.IGNORECASE)
_NUMBER_CONSTRAINT_RE = re.compile(
    r"(?P<label>[\u4e00-\u9fffA-Za-z_][\u4e00-\u9fffA-Za-z0-9_ /-]{0,18}?)\s*"
    r"(?:应|须|需|必须)?\s*"
    r"(?P<op>不得低于|不得少于|不得高于|不得超过|不低于|不少于|大于等于|≥|>=|不高于|不超过|小于等于|≤|<=|等于|为|=)\s*"
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[%％\u4e00-\u9fffA-Za-z]*)"
)
_QUANTITY_RE = re.compile(r"(?:数量|共|采购)\s*[:：为]?\s*(\d+(?:\.\d+)?)\s*([\u4e00-\u9fffA-Za-z]+)?")
_RESOLUTION_RE = re.compile(
    r"分辨率.*?(不得低于|不低于|不少于|大于等于|≥|>=|等于|为|=)\s*"
    r"(\d+)\s*[xX×]\s*(\d+)",
    re.IGNORECASE,
)


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _verified_text(document: SourceDocument, expected_type: DocumentType) -> str:
    if document.document_type is not expected_type:
        raise ValueError(
            f"Expected {expected_type.value}, got {document.document_type.value}: {document.relative_path}"
        )
    payload = document.path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != document.source_hash:
        raise ValueError(f"Source changed after intake: {document.relative_path}")
    return payload.decode("utf-8-sig")


def _flatten_json(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[str, str, Scalar]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield from _flatten_json(child, (*path, str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _flatten_json(child, (*path, str(index)))
    elif value is None or isinstance(value, (str, int, float, bool)):
        pointer = "/" + "/".join(part.replace("~", "~0").replace("/", "~1") for part in path)
        yield ".".join(path), pointer or "/", value


def load_bidder_profile(document: SourceDocument) -> BidderProfile:
    """Load a JSON bidder profile into evidence-bound scalar facts."""

    text = _verified_text(document, DocumentType.JSON)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("bidder_profile.json must contain a JSON object")

    facts: list[BidderFact] = []
    evidence: list[EvidenceRef] = []
    for key, pointer, value in _flatten_json(data):
        excerpt = json.dumps(value, ensure_ascii=False, sort_keys=True)
        evidence_id = _stable_id("ev", document.source_hash, pointer, excerpt)
        ref = EvidenceRef(
            evidence_id=evidence_id,
            source_document_id=document.document_id,
            source_path=document.relative_path,
            source_hash=document.source_hash,
            locator=f"json:{pointer}",
            excerpt=excerpt,
            extracted_value=None if value is None else str(value),
            confidence=1.0,
        )
        evidence.append(ref)
        facts.append(BidderFact(key=key, value=value, evidence_id=evidence_id))

    legal_name: str | None = None
    for alias in ("legal_name", "company_name", "bidder_name", "企业名称", "公司名称", "name", "名称"):
        candidate = data.get(alias)
        if isinstance(candidate, str) and candidate.strip():
            legal_name = candidate.strip()
            break
    return BidderProfile(
        source_document_id=document.document_id,
        source_hash=document.source_hash,
        legal_name=legal_name,
        facts=tuple(facts),
        evidence=tuple(evidence),
    )


def _first(row: Mapping[str, str], aliases: tuple[str, ...]) -> str | None:
    normalized = {key.strip().casefold(): (value.strip() if value is not None else "") for key, value in row.items()}
    for alias in aliases:
        value = normalized.get(alias.casefold())
        if value:
            return value
    return None


def _price(raw: str | None) -> float | None:
    if raw is None:
        return None
    cleaned = re.sub(r"[^0-9.+-]", "", raw.replace(",", ""))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def load_catalog(document: SourceDocument) -> tuple[CatalogItem, ...]:
    """Load a UTF-8 CSV catalog; absent values remain ``None``."""

    text = _verified_text(document, DocumentType.CSV)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("catalog.csv must contain a header row")

    items: list[CatalogItem] = []
    for row_number, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        raw_id = _first(row, _ID_ALIASES)
        name = _first(row, _NAME_ALIASES)
        model = _first(row, _MODEL_ALIASES)
        item_id = raw_id or _stable_id("item", document.source_hash, str(row_number))
        excerpt = json.dumps(row, ensure_ascii=False, sort_keys=True)
        evidence_id = _stable_id("ev", document.source_hash, f"row:{row_number}", excerpt)
        ref = EvidenceRef(
            evidence_id=evidence_id,
            source_document_id=document.document_id,
            source_path=document.relative_path,
            source_hash=document.source_hash,
            locator=f"row:{row_number}",
            excerpt=excerpt,
            extracted_value=item_id,
            confidence=1.0,
        )
        certificate_text = _first(row, _CERT_ALIASES) or ""
        certifications = tuple(
            item.strip()
            for item in re.split(r"[,，;；|]", certificate_text)
            if item.strip()
        )
        reserved = {
            alias.casefold()
            for aliases in (
                _ID_ALIASES,
                _NAME_ALIASES,
                _MODEL_ALIASES,
                _CATEGORY_ALIASES,
                _UNIT_ALIASES,
                _PRICE_ALIASES,
                _CURRENCY_ALIASES,
                _CERT_ALIASES,
            )
            for alias in aliases
        }
        attributes: dict[str, Scalar] = {
            key.strip(): (value.strip() or None)
            for key, value in row.items()
            if key and key.strip().casefold() not in reserved
        }
        items.append(
            CatalogItem(
                item_id=item_id,
                name=name,
                model=model,
                category=_first(row, _CATEGORY_ALIASES),
                unit=_first(row, _UNIT_ALIASES),
                unit_price=_price(_first(row, _PRICE_ALIASES)),
                currency=_first(row, _CURRENCY_ALIASES),
                attributes=attributes,
                certifications=certifications,
                evidence_ids=(evidence_id,),
                evidence=(ref,),
            )
        )
    return tuple(items)


def _catalog_blob(item: CatalogItem) -> str:
    values = [item.name, item.model, item.category, *item.certifications]
    values.extend(str(value) for value in item.attributes.values() if value is not None)
    return " ".join(value for value in values if value).casefold()


def _candidate_score(requirement: Requirement, item: CatalogItem) -> int:
    text = requirement.text.casefold()
    score = 0
    for value, weight in ((item.model, 8), (item.name, 6), (item.category, 3)):
        if value and len(value.strip()) >= 2 and value.casefold() in text:
            score += weight
    for key in item.attributes:
        if len(key.strip()) >= 2 and key.casefold() in text:
            score += 2
    for cert in item.certifications:
        if len(cert) >= 3 and cert.casefold() in text:
            score += 4
    intent = _product_intent(requirement.text)
    if intent and _item_intent(item) == intent:
        score += 12
    return score


def _product_intent(text: str) -> str | None:
    if "控制终端" in text or "控制主机" in text:
        return "controller"
    if "显示设备" in text or "显示终端" in text or "屏幕尺寸" in text:
        return "display"
    return None


def _item_intent(item: CatalogItem) -> str | None:
    category = (item.category or "").casefold()
    name = (item.name or "").casefold()
    if category in {"display", "screen", "显示"} or "显示" in name:
        return "display"
    if category in {"controller", "control", "terminal", "控制终端"} or "控制终端" in name:
        return "controller"
    return None


def _choose_candidate(requirement: Requirement, catalog: tuple[CatalogItem, ...]) -> tuple[CatalogItem | None, int]:
    intent = _product_intent(requirement.text)
    candidates = tuple(item for item in catalog if not intent or _item_intent(item) == intent)
    ranked = sorted(
        (
            (item, _candidate_score(requirement, item) + _constraint_fit(requirement, item))
            for item in candidates
        ),
        key=lambda pair: (-pair[1], pair[0].item_id),
    )
    if not ranked:
        return None, 0
    if ranked[0][1] > 0:
        return ranked[0]
    if len(ranked) == 1:
        return ranked[0][0], 0
    return None, 0


def _constraint_fit(requirement: Requirement, item: CatalogItem) -> int:
    score = 0
    for constraint in _NUMBER_CONSTRAINT_RE.finditer(requirement.text):
        if any(term in constraint.group("label") for term in ("数量", "采购", "分辨率")):
            continue
        _, actual = _candidate_value(item, constraint.group("label"))
        if actual is None:
            continue
        expected = float(constraint.group("value"))
        score += 8 if _compare(actual, constraint.group("op"), expected) else -40
    resolution = _resolution_check(requirement, item)
    if resolution is not None and resolution[0] is not None:
        score += 12 if resolution[0] else -60
    return score


def _number(raw: Scalar) -> float | None:
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(raw).replace(",", ""))
    return float(match.group()) if match else None


def _candidate_value(item: CatalogItem, label: str) -> tuple[str | None, float | None]:
    compact_label = re.sub(r"[\s_/-]", "", label).casefold()
    aliases: dict[str, Scalar] = dict(item.attributes)
    aliases.update({"单价": item.unit_price, "价格": item.unit_price, "型号": item.model})
    ranked: list[tuple[int, str, Scalar]] = []
    semantic_aliases = {
        "screen_inches": ("屏幕尺寸", "屏幕", "尺寸", "英寸"),
        "resolution": ("分辨率",),
        "memory_gb": ("内存", "运行内存"),
        "storage_gb": ("存储容量", "存储", "硬盘"),
        "warranty_years": ("质保", "质保期", "原厂质保"),
    }
    for key, value in aliases.items():
        compact_key = re.sub(r"[\s_/-]", "", key).casefold()
        if not compact_key:
            continue
        translated = semantic_aliases.get(key.casefold(), ())
        semantic_match = any(
            re.sub(r"\s", "", alias).casefold() in compact_label for alias in translated
        )
        if compact_key in compact_label or compact_label.endswith(compact_key) or semantic_match:
            ranked.append((len(compact_key), key, value))
    if not ranked:
        return None, None
    _, key, value = max(ranked)
    return f"{key}={value}", _number(value)


def _compare(actual: float, operator: str, expected: float) -> bool:
    if operator in ("不得低于", "不得少于", "不低于", "不少于", "大于等于", "≥", ">="):
        return actual >= expected
    if operator in ("不得高于", "不得超过", "不高于", "不超过", "小于等于", "≤", "<="):
        return actual <= expected
    return actual == expected


def _resolution_check(
    requirement: Requirement, item: CatalogItem
) -> tuple[bool | None, str, str | None] | None:
    expected = _RESOLUTION_RE.search(requirement.text)
    if expected is None:
        return None
    raw_actual = next(
        (
            value
            for key, value in item.attributes.items()
            if key.casefold() in {"resolution", "分辨率"}
        ),
        None,
    )
    actual = re.search(r"(\d+)\s*[xX×]\s*(\d+)", str(raw_actual or ""))
    expected_text = f"分辨率{expected.group(1)}{expected.group(2)}×{expected.group(3)}"
    if actual is None:
        return None, expected_text, None
    expected_pair = (float(expected.group(2)), float(expected.group(3)))
    actual_pair = (float(actual.group(1)), float(actual.group(2)))
    operator = expected.group(1)
    passed = all(
        _compare(actual_value, operator, expected_value)
        for actual_value, expected_value in zip(actual_pair, expected_pair, strict=True)
    )
    return passed, expected_text, f"分辨率={actual.group(1)}×{actual.group(2)}"


def _fact_groups(profile: BidderProfile) -> dict[str, dict[str, BidderFact]]:
    groups: dict[str, dict[str, BidderFact]] = {}
    for fact in profile.facts:
        prefix, separator, leaf = fact.key.rpartition(".")
        if not separator:
            prefix, leaf = "", fact.key
        groups.setdefault(prefix, {})[leaf.casefold()] = fact
    return groups


def _normalized(value: object) -> str:
    return re.sub(r"\s+", "", str(value)).casefold()


def _profile_support_for_terms(
    profile: BidderProfile,
    terms: Iterable[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    normalized_terms = tuple(dict.fromkeys(_normalized(term) for term in terms if term))
    present: list[str] = []
    evidence_ids: list[str] = []
    for term in normalized_terms:
        matched = [
            fact
            for fact in profile.facts
            if fact.value is not None and term in _normalized(f"{fact.key}={fact.value}")
        ]
        if matched:
            present.append(term)
            evidence_ids.extend(fact.evidence_id for fact in matched)
    return tuple(present), tuple(dict.fromkeys(evidence_ids))


def _pricing_policy_match(
    requirement: Requirement,
    profile: BidderProfile,
) -> tuple[MatchStatus, str, str | None, tuple[str, ...]] | None:
    if "暂估价格" not in requirement.text:
        return None
    final_facts = [
        fact
        for fact in profile.facts
        if fact.value is not None
        and (
            (fact.key.casefold().endswith("quote_basis") and _normalized(fact.value) in {"final", "正式报价"})
            or (fact.key.casefold().endswith("is_provisional") and fact.value is False)
        )
    ]
    evidence_ids = tuple(dict.fromkeys(fact.evidence_id for fact in final_facts))
    if len(final_facts) >= 2:
        return (
            MatchStatus.COMPLIANT,
            "主体报价依据明确为正式报价且未使用暂估价格",
            "quote_basis=final；is_provisional=false",
            evidence_ids,
        )
    return (
        MatchStatus.UNKNOWN,
        "主体资料未同时证明报价为正式报价且未使用暂估价格",
        None,
        evidence_ids,
    )


def _submission_deadline_match(
    requirement: Requirement,
    profile: BidderProfile,
) -> tuple[MatchStatus, str, str | None, tuple[str, ...]] | None:
    if "截止" not in requirement.text and "递交" not in requirement.text:
        return None
    deadline = re.search(
        r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*(\d{1,2}):?(\d{2})?",
        requirement.text,
    )
    if deadline is None:
        return None
    normalized_deadline = (
        f"{deadline.group(1)}-{int(deadline.group(2)):02d}-{int(deadline.group(3)):02d} "
        f"{int(deadline.group(4)):02d}:{int(deadline.group(5) or 0):02d}"
    )
    matching = [
        fact
        for fact in profile.facts
        if fact.value is not None
        and fact.key.casefold().endswith("deadline")
        and _normalized(fact.value) == _normalized(normalized_deadline)
    ]
    acknowledged = [
        fact
        for fact in profile.facts
        if fact.key.casefold().endswith("deadline_acknowledged") and fact.value is True
    ]
    evidence_ids = tuple(
        dict.fromkeys(fact.evidence_id for fact in (*matching, *acknowledged))
    )
    if matching and acknowledged:
        return (
            MatchStatus.COMPLIANT,
            "递交截止时间已被确定性提取并登记为受控人工提交约束",
            f"deadline={normalized_deadline}；acknowledged=true",
            evidence_ids,
        )
    return (
        MatchStatus.UNKNOWN,
        "递交截止时间尚未在主体提交控制中完整登记",
        None,
        evidence_ids,
    )


def _duration_profile_match(
    requirement: Requirement, profile: BidderProfile
) -> tuple[MatchStatus, str, str | None, tuple[str, ...]] | None:
    if "交付" not in requirement.text:
        return None
    expected_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:个\s*)?(?:自然日|工作日|日|天)内",
        requirement.text,
    )
    if expected_match is None:
        return None
    expected_days = float(expected_match.group(1))
    for group in _fact_groups(profile).values():
        name = group.get("name")
        value = group.get("value")
        if name is None or "交付周期" not in str(name.value):
            continue
        actual_days = _number(value.value) if value is not None else None
        supporting = tuple(
            fact.evidence_id for fact in (name, value) if fact is not None
        )
        if actual_days is None:
            return (
                MatchStatus.UNKNOWN,
                "主体资料声明了交付周期，但没有可解析的周期值",
                None,
                supporting,
            )
        actual = f"交付周期={value.value}"
        if actual_days <= expected_days:
            return (
                MatchStatus.COMPLIANT,
                f"主体资料交付周期 {actual_days:g} 天不超过要求的 {expected_days:g} 天",
                actual,
                supporting,
            )
        return (
            MatchStatus.NON_COMPLIANT,
            f"主体资料交付周期 {actual_days:g} 天超过要求的 {expected_days:g} 天",
            actual,
            supporting,
        )
    return (
        MatchStatus.UNKNOWN,
        "主体资料未提供可核验的交付周期",
        None,
        (),
    )


def _qualification_document_match(
    requirement: Requirement, profile: BidderProfile
) -> tuple[MatchStatus, str, str | None, tuple[str, ...]] | None:
    terms = [term for term in _PROFILE_TERMS if term in requirement.text]
    terms.extend(match.group(0).replace(" ", "") for match in _ISO_RE.finditer(requirement.text))
    if not terms:
        return None
    groups = _fact_groups(profile)
    matched_groups: list[dict[str, BidderFact]] = []
    missing_terms: list[str] = []
    for term in terms:
        match = next(
            (
                group
                for group in groups.values()
                if (name := group.get("name")) is not None
                and _normalized(term) in _normalized(name.value)
            ),
            None,
        )
        if match is None:
            missing_terms.append(term)
        else:
            matched_groups.append(match)
    if missing_terms:
        return (
            MatchStatus.UNKNOWN,
            f"主体资料未找到文件：{', '.join(missing_terms)}；缺失不等于不合规",
            None,
            tuple(
                fact.evidence_id for group in matched_groups for fact in group.values()
            ),
        )

    supporting = tuple(
        dict.fromkeys(fact.evidence_id for group in matched_groups for fact in group.values())
    )
    actual_parts: list[str] = []
    for group in matched_groups:
        name = group["name"]
        status_fact = group.get("status")
        status = _normalized(status_fact.value) if status_fact is not None else ""
        actual_parts.append(
            f"{name.value} status={status_fact.value if status_fact is not None else 'unknown'}"
        )
        if "有效" in requirement.text and status not in {"valid", "有效"}:
            if status in {"invalid", "expired", "无效", "过期"}:
                return (
                    MatchStatus.NON_COMPLIANT,
                    f"主体资料明确标记 {name.value} 为 {status_fact.value}",
                    "；".join(actual_parts),
                    supporting,
                )
            return (
                MatchStatus.UNKNOWN,
                f"主体资料存在 {name.value}，但未提供 valid/有效状态",
                "；".join(actual_parts),
                supporting,
            )
    return (
        MatchStatus.COMPLIANT,
        "主体资料中找到要求的文件且状态为 valid/有效",
        "；".join(actual_parts),
        supporting,
    )


def _profile_match(
    requirement: Requirement, profile: BidderProfile
) -> tuple[MatchStatus, str, str | None, tuple[str, ...]]:
    duration_result = _duration_profile_match(requirement, profile)
    if duration_result is not None:
        return duration_result
    pricing_policy = _pricing_policy_match(requirement, profile)
    if pricing_policy is not None:
        return pricing_policy
    submission_deadline = _submission_deadline_match(requirement, profile)
    if submission_deadline is not None:
        return submission_deadline
    if requirement.category is RequirementCategory.QUALIFICATION:
        document_result = _qualification_document_match(requirement, profile)
        if document_result is not None:
            return document_result
    blob = " ".join(f"{fact.key}={fact.value}" for fact in profile.facts if fact.value is not None).casefold()
    terms = [term for term in _PROFILE_TERMS if term in requirement.text]
    if "交付" in requirement.text and re.search(r"\d+\s*(?:个\s*)?(?:自然日|工作日|日|天)", requirement.text):
        terms.append("交付周期")
    terms.extend(match.group(0).replace(" ", "") for match in _ISO_RE.finditer(requirement.text))
    if not profile.facts:
        return MatchStatus.UNKNOWN, "投标主体资料为空，不能推断满足要求", None, ()
    if not terms:
        return MatchStatus.UNKNOWN, "未找到可由主体资料确定性核对的关键字段", None, ()
    present = [term for term in terms if term.casefold() in blob.replace(" ", "")]
    supporting_ids = tuple(
        fact.evidence_id
        for fact in profile.facts
        if any(
            term.casefold() in f"{fact.key}={fact.value}".replace(" ", "").casefold()
            for term in present
        )
    )
    if len(present) == len(terms):
        return (
            MatchStatus.COMPLIANT,
            f"主体资料中找到明确字段：{', '.join(present)}",
            ", ".join(present),
            supporting_ids,
        )
    if present:
        missing = [term for term in terms if term not in present]
        return (
            MatchStatus.PARTIAL,
            f"仅找到部分字段；仍缺：{', '.join(missing)}",
            ", ".join(present),
            supporting_ids,
        )
    return (
        MatchStatus.UNKNOWN,
        f"资料中未找到字段：{', '.join(terms)}；缺失不等于不合规",
        None,
        (),
    )


def _warranty_match(
    requirement: Requirement, selected: tuple[CatalogItem, ...]
) -> tuple[MatchStatus, str, str | None, tuple[str, ...]]:
    expected_match = re.search(
        r"(?:不少于|不低于|不得少于|不得低于)\s*(\d+(?:\.\d+)?)\s*年.*?(?:质保|保修)",
        requirement.text,
    ) or re.search(
        r"(?:质保|保修).*?(?:不少于|不低于|不得少于|不得低于)\s*(\d+(?:\.\d+)?)\s*年",
        requirement.text,
    )
    if expected_match is None:
        return MatchStatus.UNKNOWN, "质保要求无法解析为确定性年限", None, ()
    expected_years = float(expected_match.group(1))
    if not selected:
        return MatchStatus.UNKNOWN, "尚无已选核心设备，无法聚合检查质保", None, ()
    actuals: list[tuple[CatalogItem, float | None]] = []
    for item in selected:
        value = next(
            (
                candidate
                for key, candidate in item.attributes.items()
                if key.casefold() == "warranty_years"
            ),
            None,
        )
        actuals.append((item, _number(value)))
    evidence_ids = tuple(
        dict.fromkeys(evidence_id for item, _ in actuals for evidence_id in item.evidence_ids)
    )
    actual = "；".join(
        f"{item.item_id}={years:g}年" if years is not None else f"{item.item_id}=unknown"
        for item, years in actuals
    )
    if any(years is None for _, years in actuals):
        return MatchStatus.PARTIAL, "部分已选设备缺少质保年限", actual, evidence_ids
    failed = [(item, years) for item, years in actuals if years is not None and years < expected_years]
    if failed:
        return (
            MatchStatus.NON_COMPLIANT,
            f"已选设备中存在质保低于 {expected_years:g} 年的项目",
            actual,
            evidence_ids,
        )
    return (
        MatchStatus.COMPLIANT,
        f"全部 {len(actuals)} 个已选核心设备质保均不低于 {expected_years:g} 年",
        actual,
        evidence_ids,
    )


def _pricing_total_match(
    requirement: Requirement,
    bom: tuple[BOMLine, ...],
    profile: BidderProfile,
) -> tuple[MatchStatus, str, str | None, tuple[str, ...]] | None:
    limit_match = re.search(
        r"(?:总报价|最高限价|预算).*?(?:不得超过|不超过|不高于|为)\s*(?:人民币|CNY|￥|¥)?\s*"
        r"([\d,]+(?:\.\d+)?)",
        requirement.text,
        re.IGNORECASE,
    )
    if limit_match is None:
        return None
    limit = float(limit_match.group(1).replace(",", ""))
    if not bom or any(line.qty is None or line.unit_price is None for line in bom):
        return MatchStatus.UNKNOWN, "BOM 数量或目录单价不完整，无法核对报价上限", None, ()
    subtotal = sum((line.qty or 0.0) * (line.unit_price or 0.0) for line in bom)
    evidence_ids = tuple(
        dict.fromkeys(evidence_id for line in bom for evidence_id in line.evidence_ids)
    )
    actual = f"目录硬件小计={subtotal:.2f}"
    if subtotal > limit:
        return (
            MatchStatus.NON_COMPLIANT,
            f"目录硬件小计 {subtotal:.2f} 超过总报价上限 {limit:.2f}",
            actual,
            evidence_ids,
        )
    if any(term in requirement.text for term in ("包含", "含运输", "含安装", "含税")):
        required_terms = ("运输", "安装", "培训", "税费")
        present, profile_evidence_ids = _profile_support_for_terms(profile, required_terms)
        quote_final = [
            fact
            for fact in profile.facts
            if fact.key.casefold().endswith("quote_basis")
            and _normalized(fact.value) in {"final", "正式报价"}
        ]
        supporting = tuple(
            dict.fromkeys(
                (*evidence_ids, *profile_evidence_ids, *(fact.evidence_id for fact in quote_final))
            )
        )
        if len(present) == len(required_terms) and quote_final:
            return (
                MatchStatus.COMPLIANT,
                f"目录硬件小计 {subtotal:.2f} 未超过 {limit:.2f}，且主体资料逐项证明运输、安装、培训和税费已纳入正式报价",
                actual + "；运输/安装/培训/税费已包含；quote_basis=final",
                supporting,
            )
        return (
            MatchStatus.PARTIAL,
            f"目录硬件小计 {subtotal:.2f} 未超过 {limit:.2f}，但未证明已包含运输、安装、培训或税费",
            actual,
            tuple(dict.fromkeys((*evidence_ids, *profile_evidence_ids))),
        )
    return (
        MatchStatus.COMPLIANT,
        f"目录硬件小计 {subtotal:.2f} 未超过报价上限 {limit:.2f}",
        actual,
        evidence_ids,
    )


def _catalog_match(
    requirement: Requirement, catalog: tuple[CatalogItem, ...]
) -> tuple[MatchStatus, str, CatalogItem | None, str | None, str | None]:
    candidate, score = _choose_candidate(requirement, catalog)
    if candidate is None:
        return MatchStatus.UNKNOWN, "目录中没有可解释匹配的候选产品", None, requirement.text, None

    constraints = list(_NUMBER_CONSTRAINT_RE.finditer(requirement.text))
    evaluated: list[str] = []
    unknown: list[str] = []
    failed: list[str] = []
    for constraint in constraints:
        label = constraint.group("label").strip()
        if any(term in label for term in ("数量", "采购", "分辨率")):
            continue
        operator = constraint.group("op")
        expected_number = float(constraint.group("value"))
        actual_text, actual_number = _candidate_value(candidate, label)
        expected_text = f"{label}{operator}{constraint.group('value')}{constraint.group('unit')}"
        if actual_number is None:
            unknown.append(expected_text)
        elif _compare(actual_number, operator, expected_number):
            evaluated.append(f"{expected_text}，实际 {actual_text}")
        else:
            failed.append(f"{expected_text}，实际 {actual_text}")

    resolution = _resolution_check(requirement, candidate)
    if resolution is not None:
        passed, expected_text, actual_text = resolution
        if passed is None:
            unknown.append(expected_text)
        elif passed:
            evaluated.append(f"{expected_text}，实际 {actual_text}")
        else:
            failed.append(f"{expected_text}，实际 {actual_text}")

    candidate_name = candidate.name or candidate.model or candidate.item_id
    if failed:
        return (
            MatchStatus.NON_COMPLIANT,
            f"候选 {candidate_name} 存在明确参数偏离：{'；'.join(failed)}",
            candidate,
            "；".join(failed),
            "；".join(failed),
        )
    if unknown:
        status = MatchStatus.PARTIAL if evaluated or score > 0 else MatchStatus.UNKNOWN
        rationale = f"候选 {candidate_name} 仍有无法核验的参数：{'；'.join(unknown)}"
        return status, rationale, candidate, "；".join(unknown), "；".join(evaluated) or None
    if constraints and evaluated:
        return (
            MatchStatus.COMPLIANT,
            f"候选 {candidate_name} 的确定性参数检查通过：{'；'.join(evaluated)}",
            candidate,
            "；".join(match.group(0) for match in constraints),
            "；".join(evaluated),
        )
    if score > 0:
        return MatchStatus.PARTIAL, f"候选 {candidate_name} 名称/字段相关，但要求缺少可完全核验的结构化条件", candidate, requirement.text, candidate_name
    return MatchStatus.UNKNOWN, f"仅有一个目录候选 {candidate_name}，不足以证明满足要求", candidate, requirement.text, candidate_name


def _quantity(text: str) -> tuple[float | None, str | None]:
    match = _QUANTITY_RE.search(text)
    if not match:
        return None, None
    return float(match.group(1)), match.group(2)


def build_analysis(
    task_id: str,
    extraction: ExtractionResult,
    profile: BidderProfile,
    catalog: Iterable[CatalogItem],
) -> AnalysisBundle:
    """Build conservative compliance, gaps, deviations and a BOM baseline."""

    catalog_items = tuple(catalog)
    matches: list[ComplianceMatch] = []
    missing_items: list[MissingItem] = []
    deviations: list[Deviation] = []
    bom: list[BOMLine] = []
    assessed_requirements: list[Requirement] = []
    selected_catalog: dict[str, CatalogItem] = {}

    for requirement in extraction.requirements:
        pricing_result = (
            _pricing_total_match(requirement, tuple(bom), profile)
            if requirement.category is RequirementCategory.PRICING
            else None
        )
        pricing_policy = (
            _pricing_policy_match(requirement, profile)
            if requirement.category is RequirementCategory.PRICING
            else None
        )
        if (
            requirement.category is RequirementCategory.TECHNICAL
            and ("质保" in requirement.text or "保修" in requirement.text)
            and _product_intent(requirement.text) is None
        ):
            status, rationale, actual, supporting_evidence_ids = _warranty_match(
                requirement, tuple(selected_catalog.values())
            )
            candidate = None
            expected = requirement.text
        elif pricing_policy is not None:
            status, rationale, actual, supporting_evidence_ids = pricing_policy
            candidate = None
            expected = requirement.text
        elif pricing_result is not None:
            status, rationale, actual, supporting_evidence_ids = pricing_result
            candidate = None
            expected = requirement.text
        elif requirement.category in (RequirementCategory.TECHNICAL, RequirementCategory.PRICING):
            status, rationale, candidate, expected, actual = _catalog_match(requirement, catalog_items)
            supporting_evidence_ids: tuple[str, ...] = ()
        else:
            status, rationale, actual, supporting_evidence_ids = _profile_match(requirement, profile)
            candidate = None
            expected = requirement.text

        evidence_ids = list(requirement.evidence_ids)
        evidence_ids.extend(supporting_evidence_ids)
        if candidate is not None:
            evidence_ids.extend(candidate.evidence_ids)
        unique_evidence_ids = tuple(dict.fromkeys(evidence_ids))
        if (
            candidate is not None
            and requirement.category is RequirementCategory.TECHNICAL
            and _product_intent(requirement.text)
        ):
            selected_catalog.setdefault(candidate.item_id, candidate)
        match_id = _stable_id("match", task_id, requirement.req_id)
        matches.append(
            ComplianceMatch(
                match_id=match_id,
                requirement_id=requirement.req_id,
                status=status,
                rationale=rationale,
                candidate_id=candidate.item_id if candidate else None,
                expected=expected,
                actual=actual,
                evidence_ids=unique_evidence_ids,
            )
        )
        assessed_requirements.append(replace(requirement, status=status))

        if status in (MatchStatus.UNKNOWN, MatchStatus.PARTIAL, MatchStatus.NON_COMPLIANT):
            missing_items.append(
                MissingItem(
                    id=_stable_id("missing", task_id, requirement.req_id),
                    requirement_id=requirement.req_id,
                    description=f"需人工补充或确认：{requirement.text}",
                    severity=Severity.BLOCKER if requirement.mandatory else Severity.WARNING,
                    blocks_completion=requirement.mandatory,
                )
            )
        if status in (MatchStatus.NON_COMPLIANT, MatchStatus.PARTIAL):
            deviations.append(
                Deviation(
                    id=_stable_id("dev", task_id, requirement.req_id),
                    requirement_id=requirement.req_id,
                    expected=expected,
                    actual=actual,
                    status=status,
                    evidence_ids=unique_evidence_ids,
                    explanation=rationale,
                )
            )

        if requirement.category is RequirementCategory.TECHNICAL and _product_intent(requirement.text):
            qty, parsed_unit = _quantity(requirement.text)
            bom.append(
                BOMLine(
                    id=_stable_id("bom", task_id, requirement.req_id),
                    requirement_id=requirement.req_id,
                    item_id=candidate.item_id if candidate else None,
                    name=candidate.name if candidate else None,
                    qty=qty,
                    unit=parsed_unit or (candidate.unit if candidate else None),
                    unit_price=candidate.unit_price if candidate else None,
                    currency=candidate.currency if candidate else None,
                    status=status,
                    evidence_ids=unique_evidence_ids,
                    rationale=rationale,
                )
            )

    evidence_by_id: dict[str, EvidenceRef] = {ref.evidence_id: ref for ref in extraction.evidence}
    evidence_by_id.update({ref.evidence_id: ref for ref in profile.evidence})
    for item in catalog_items:
        evidence_by_id.update({ref.evidence_id: ref for ref in item.evidence})

    return AnalysisBundle(
        task_id=task_id,
        requirements=tuple(assessed_requirements),
        evidence=tuple(evidence_by_id.values()),
        matches=tuple(matches),
        bom=tuple(bom),
        deviations=tuple(deviations),
        missing_items=tuple(missing_items),
    )


__all__ = ["build_analysis", "load_bidder_profile", "load_catalog"]
