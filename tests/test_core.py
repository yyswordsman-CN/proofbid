from __future__ import annotations

from pathlib import Path

import pytest

from proofbid import (
    MatchStatus,
    OversizedDocumentError,
    PathBoundaryError,
    RequirementCategory,
    UnsupportedDocumentError,
    build_analysis,
    extract_requirements,
    load_bidder_profile,
    load_catalog,
    scan_workspace,
)


FIXTURE = Path(__file__).parents[1] / "examples" / "synthetic_tender"


def _bundle():
    documents = scan_workspace(
        FIXTURE,
        ("tender.md", "bidder_profile.json", "catalog.csv"),
    )
    by_name = {document.relative_path: document for document in documents}
    extraction = extract_requirements((by_name["tender.md"],))
    profile = load_bidder_profile(by_name["bidder_profile.json"])
    catalog = load_catalog(by_name["catalog.csv"])
    return extraction, build_analysis("oracle", extraction, profile, catalog)


def test_extraction_is_evidence_bound_and_section_aware() -> None:
    extraction, _ = _bundle()

    assert len(extraction.requirements) == 12
    assert all(not evidence.excerpt.startswith(">") for evidence in extraction.evidence)
    evidence_ids = {evidence.evidence_id for evidence in extraction.evidence}
    assert all(set(requirement.evidence_ids) <= evidence_ids for requirement in extraction.requirements)

    by_line = {requirement.source_locator: requirement for requirement in extraction.requirements}
    assert by_line["line:19"].mandatory is True
    assert by_line["line:30"].category is RequirementCategory.SUBMISSION


def test_matching_oracle_preserves_unknowns_and_builds_explainable_bom() -> None:
    _, bundle = _bundle()
    matches = {
        requirement.source_locator: match
        for requirement, match in zip(bundle.requirements, bundle.matches, strict=True)
    }

    assert [(line.item_id, line.qty) for line in bundle.bom] == [
        ("DISPLAY-98", 2.0),
        ("CONTROL-16", 1.0),
    ]
    assert sum((line.qty or 0) * (line.unit_price or 0) for line in bundle.bom) == 274_000

    warranty = matches["line:15"]
    assert warranty.status is MatchStatus.COMPLIANT
    assert warranty.actual == "DISPLAY-98=3年；CONTROL-16=3年"
    assert len(warranty.evidence_ids) == 3  # tender line plus both selected catalog rows

    delivery = matches["line:19"]
    assert delivery.status is MatchStatus.COMPLIANT
    assert delivery.actual == "交付周期=20 个自然日"
    assert "20 天不超过要求的 30 天" in delivery.rationale

    pricing = matches["line:24"]
    assert pricing.status is MatchStatus.PARTIAL
    assert pricing.actual == "目录硬件小计=274000.00"
    assert "未证明已包含" in pricing.rationale

    assert "status=valid" in (matches["line:7"].actual or "")
    assert "status=valid" in (matches["line:8"].actual or "")

    authorization = next(
        (requirement, match)
        for requirement, match in zip(bundle.requirements, bundle.matches, strict=True)
        if "授权书" in requirement.text
    )
    assert authorization[1].status is MatchStatus.UNKNOWN
    assert authorization[1].candidate_id is None
    assert any(
        item.requirement_id == authorization[0].req_id and item.blocks_completion
        for item in bundle.missing_items
    )


def test_resolution_compares_both_dimensions(tmp_path: Path) -> None:
    for name in ("tender.md", "bidder_profile.json", "catalog.csv"):
        content = (FIXTURE / name).read_text(encoding="utf-8")
        if name == "catalog.csv":
            content = content.replace("DISPLAY-98,智慧会议显示设备,PB-X98,display,98,3840x2160", "DISPLAY-98,智慧会议显示设备,PB-X98,display,98,3840x1080")
        (tmp_path / name).write_text(content, encoding="utf-8")

    documents = scan_workspace(tmp_path)
    by_name = {document.relative_path: document for document in documents}
    extraction = extract_requirements((by_name["tender.md"],))
    bundle = build_analysis(
        "resolution-oracle",
        extraction,
        load_bidder_profile(by_name["bidder_profile.json"]),
        load_catalog(by_name["catalog.csv"]),
    )
    display_match = next(
        match
        for requirement, match in zip(bundle.requirements, bundle.matches, strict=True)
        if requirement.source_locator == "line:13"
    )
    assert display_match.status is not MatchStatus.COMPLIANT


def test_intake_blocks_boundary_unknown_type_and_oversize(tmp_path: Path) -> None:
    safe = tmp_path / "safe"
    safe.mkdir()
    (safe / "tender.md").write_text("# 技术要求\n- 必须提供说明", encoding="utf-8")
    assert len(scan_workspace(safe)) == 1

    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    with pytest.raises(PathBoundaryError):
        scan_workspace(safe, ("../outside.md",))

    (safe / "payload.bin").write_bytes(b"not accepted")
    with pytest.raises(UnsupportedDocumentError):
        scan_workspace(safe)
    (safe / "payload.bin").unlink()

    (safe / "large.txt").write_text("12345", encoding="utf-8")
    with pytest.raises(OversizedDocumentError):
        scan_workspace(safe, max_file_bytes=4)
