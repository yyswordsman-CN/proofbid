"""Vendor-neutral contracts and policy for model-produced execution plans.

The planner may describe an execution graph, but it never supplies paths,
arguments, code, or domain facts.  A locally enforced policy binds every plan
to an immutable :class:`TaskSpec` before the deterministic pipeline may run.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Mapping, Protocol

from .contracts import DocumentType, SourceDocument


TASK_SPEC_SCHEMA_VERSION = "proofbid.task-spec/v1"
EXECUTION_PLAN_SCHEMA_VERSION = "proofbid.execution-plan/v1"
PROVIDER_RECEIPT_SCHEMA_VERSION = "proofbid.provider-receipt/v1"
TASK_SPEC_NAME = "task_spec.json"
EXECUTION_PLAN_NAME = "execution_plan.json"
PROVIDER_RECEIPT_NAME = "planner_receipt.json"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_STEP_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class PlanTool(str, Enum):
    """The complete tool vocabulary exposed to the planning contract."""

    SCAN_WORKSPACE = "proofbid.scan_workspace"
    EXTRACT_REQUIREMENTS = "proofbid.extract_requirements"
    LOAD_BIDDER_PROFILE = "proofbid.load_bidder_profile"
    LOAD_CATALOG = "proofbid.load_catalog"
    BUILD_ANALYSIS = "proofbid.build_analysis"
    VALIDATE_BUNDLE = "proofbid.validate_bundle"
    RENDER_BUNDLE = "proofbid.render_bundle"
    VALIDATE_ARTIFACTS = "proofbid.validate_artifacts"


TOOL_DESCRIPTIONS: Mapping[PlanTool, str] = {
    PlanTool.SCAN_WORKSPACE: "Scan only the trusted task workspace boundary and hash inputs.",
    PlanTool.EXTRACT_REQUIREMENTS: "Extract evidence-bound requirements from scanned inputs.",
    PlanTool.LOAD_BIDDER_PROFILE: "Load the typed bidder profile from the scanned manifest.",
    PlanTool.LOAD_CATALOG: "Load the typed product catalog from the scanned manifest.",
    PlanTool.BUILD_ANALYSIS: "Build matches, BOM, deviations, and missing items deterministically.",
    PlanTool.VALIDATE_BUNDLE: "Validate evidence lineage and domain readiness gates.",
    PlanTool.RENDER_BUNDLE: "Render controlled JSON, XLSX, DOCX, manifest, and ZIP artifacts.",
    PlanTool.VALIDATE_ARTIFACTS: "Validate cross-artifact content, hashes, and archive integrity.",
}


REQUIRED_TOOL_DEPENDENCIES: Mapping[PlanTool, tuple[PlanTool, ...]] = {
    PlanTool.SCAN_WORKSPACE: (),
    PlanTool.EXTRACT_REQUIREMENTS: (PlanTool.SCAN_WORKSPACE,),
    PlanTool.LOAD_BIDDER_PROFILE: (PlanTool.SCAN_WORKSPACE,),
    PlanTool.LOAD_CATALOG: (PlanTool.SCAN_WORKSPACE,),
    PlanTool.BUILD_ANALYSIS: (
        PlanTool.EXTRACT_REQUIREMENTS,
        PlanTool.LOAD_BIDDER_PROFILE,
        PlanTool.LOAD_CATALOG,
    ),
    PlanTool.VALIDATE_BUNDLE: (PlanTool.BUILD_ANALYSIS,),
    PlanTool.RENDER_BUNDLE: (PlanTool.VALIDATE_BUNDLE,),
    PlanTool.VALIDATE_ARTIFACTS: (PlanTool.RENDER_BUNDLE,),
}
CANONICAL_TOOL_ORDER = tuple(REQUIRED_TOOL_DEPENDENCIES)


class PlanningError(RuntimeError):
    """Base class for safe, user-facing planning failures."""

    reason_code = "PLANNING_FAILED"


class PlanValidationError(PlanningError):
    """Raised when a model plan violates the local execution policy."""

    reason_code = "PLAN_POLICY_REJECTED"

    def __init__(self, reason_codes: tuple[str, ...]) -> None:
        self.reason_codes = reason_codes
        super().__init__(
            "Execution plan was rejected by local policy: " + ", ".join(reason_codes)
        )


class Planner(Protocol):
    """Synchronous boundary used by the local pipeline."""

    def create_plan(self, task_spec: "TaskSpec") -> "PlanningResult": ...


@dataclass(frozen=True, slots=True)
class TaskInputRef:
    relative_path: str
    document_type: str
    source_hash: str
    size_bytes: int

    def __post_init__(self) -> None:
        candidate = PurePosixPath(self.relative_path)
        if (
            not self.relative_path
            or candidate.is_absolute()
            or ".." in candidate.parts
            or self.relative_path != candidate.as_posix()
        ):
            raise ValueError("TaskInputRef.relative_path must be a safe relative path")
        if not _SHA256_RE.fullmatch(self.source_hash):
            raise ValueError("TaskInputRef.source_hash must be a lowercase SHA-256 digest")
        if self.document_type not in {item.value for item in DocumentType}:
            raise ValueError("TaskInputRef.document_type is not registered")
        if (
            isinstance(self.size_bytes, bool)
            or not isinstance(self.size_bytes, int)
            or self.size_bytes < 0
        ):
            raise ValueError("TaskInputRef.size_bytes must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class TaskSpec:
    task_id: str
    goal: str
    inputs: tuple[TaskInputRef, ...]
    allowed_tools: tuple[PlanTool, ...]
    required_deliverables: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    max_plan_steps: int
    schema_version: str = TASK_SPEC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != TASK_SPEC_SCHEMA_VERSION:
            raise ValueError("Unsupported TaskSpec schema version")
        if not self.task_id.strip() or len(self.task_id) > 128:
            raise ValueError("TaskSpec.task_id must be non-empty and bounded")
        if not self.goal.strip() or len(self.goal) > 800:
            raise ValueError("TaskSpec.goal must be non-empty and bounded")
        if not self.inputs:
            raise ValueError("TaskSpec requires at least one input")
        input_paths = [item.relative_path for item in self.inputs]
        if input_paths != sorted(input_paths) or len(set(input_paths)) != len(input_paths):
            raise ValueError("TaskSpec inputs must be unique and sorted by relative path")
        if tuple(self.allowed_tools) != CANONICAL_TOOL_ORDER:
            raise ValueError("TaskSpec allowed tools must match the canonical tool order")
        if any(not isinstance(tool, PlanTool) for tool in self.allowed_tools):
            raise ValueError("TaskSpec allowed tools must use PlanTool values")
        if (
            isinstance(self.max_plan_steps, bool)
            or not isinstance(self.max_plan_steps, int)
            or self.max_plan_steps != len(self.allowed_tools)
        ):
            raise ValueError("TaskSpec max_plan_steps must equal the allowed tool count")
        if not self.required_deliverables or not self.prohibited_actions:
            raise ValueError("TaskSpec deliverables and prohibited actions are required")
        if len(set(self.required_deliverables)) != len(self.required_deliverables) or len(
            set(self.prohibited_actions)
        ) != len(self.prohibited_actions):
            raise ValueError("TaskSpec deliverables/actions must be unique")
        if any(
            not isinstance(item, str) or not item.strip() or len(item) > 300
            for item in (*self.required_deliverables, *self.prohibited_actions)
        ):
            raise ValueError("TaskSpec deliverables/actions must be bounded strings")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "goal": self.goal,
            "inputs": [asdict(item) for item in self.inputs],
            "allowed_tools": [tool.value for tool in self.allowed_tools],
            "required_deliverables": list(self.required_deliverables),
            "prohibited_actions": list(self.prohibited_actions),
            "max_plan_steps": self.max_plan_steps,
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class PlanStep:
    step_id: str
    tool: PlanTool
    depends_on: tuple[str, ...]
    completion_criterion: str

    def __post_init__(self) -> None:
        if not _STEP_ID_RE.fullmatch(self.step_id):
            raise ValueError(f"Invalid plan step id: {self.step_id!r}")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise ValueError(f"Plan step {self.step_id} has duplicate dependencies")
        if any(
            not isinstance(dependency, str) or not _STEP_ID_RE.fullmatch(dependency)
            for dependency in self.depends_on
        ):
            raise ValueError(f"Plan step {self.step_id} has an invalid dependency id")
        if not isinstance(self.tool, PlanTool):
            raise ValueError("PlanStep.tool must be a registered PlanTool")
        if (
            not isinstance(self.completion_criterion, str)
            or not self.completion_criterion.strip()
            or len(self.completion_criterion) > 400
        ):
            raise ValueError("Plan step completion criterion must be non-empty and bounded")

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "tool": self.tool.value,
            "depends_on": list(self.depends_on),
            "completion_criterion": self.completion_criterion,
        }


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    task_spec_digest: str
    steps: tuple[PlanStep, ...]
    summary: str
    schema_version: str = EXECUTION_PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != EXECUTION_PLAN_SCHEMA_VERSION:
            raise ValueError("Unsupported ExecutionPlan schema version")
        if not _SHA256_RE.fullmatch(self.task_spec_digest):
            raise ValueError("ExecutionPlan.task_spec_digest must be a SHA-256 digest")
        if not self.steps:
            raise ValueError("ExecutionPlan requires at least one step")
        if not isinstance(self.summary, str) or not self.summary.strip() or len(self.summary) > 600:
            raise ValueError("ExecutionPlan.summary must be non-empty and bounded")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_spec_digest": self.task_spec_digest,
            "steps": [step.to_dict() for step in self.steps],
            "summary": self.summary,
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ProviderReceipt:
    provider: str
    configured_model: str
    model_version: str | None
    auth_mode: str
    adk_version: str
    genai_version: str
    started_at: str
    duration_ms: float
    event_count: int
    invocation_id: str | None
    interaction_id: str | None
    finish_reason: str | None
    prompt_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    request_digest: str
    response_digest: str
    plan_digest: str
    schema_validated: bool
    policy_validated: bool
    schema_version: str = PROVIDER_RECEIPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PROVIDER_RECEIPT_SCHEMA_VERSION:
            raise ValueError("Unsupported ProviderReceipt schema version")
        for value in (
            self.request_digest,
            self.response_digest,
            self.plan_digest,
        ):
            if not _SHA256_RE.fullmatch(value):
                raise ValueError("ProviderReceipt digests must be lowercase SHA-256 values")
        required_text = (
            self.provider,
            self.configured_model,
            self.auth_mode,
            self.adk_version,
            self.genai_version,
            self.started_at,
        )
        optional_text = (
            self.model_version,
            self.invocation_id,
            self.interaction_id,
            self.finish_reason,
        )
        if any(
            not isinstance(value, str)
            or not value.strip()
            or len(value) > 200
            or "\n" in value
            or "\r" in value
            for value in required_text
        ):
            raise ValueError("ProviderReceipt metadata must use bounded single-line strings")
        if any(
            value is not None
            and (
                not isinstance(value, str)
                or len(value) > 300
                or "\n" in value
                or "\r" in value
            )
            for value in optional_text
        ):
            raise ValueError("ProviderReceipt optional metadata must be bounded")
        if self.auth_mode not in {"api_key", "vertex_ai", "test"}:
            raise ValueError("ProviderReceipt auth mode is not registered")
        if (
            isinstance(self.event_count, bool)
            or not isinstance(self.event_count, int)
            or isinstance(self.duration_ms, bool)
            or not isinstance(self.duration_ms, (int, float))
            or not math.isfinite(self.duration_ms)
            or self.duration_ms < 0
            or self.event_count < 1
        ):
            raise ValueError("ProviderReceipt duration/event count must be valid")
        for token_count in (self.prompt_tokens, self.output_tokens, self.total_tokens):
            if token_count is not None and (
                isinstance(token_count, bool)
                or not isinstance(token_count, int)
                or token_count < 0
            ):
                raise ValueError("ProviderReceipt token counts must be non-negative integers")
        if not isinstance(self.schema_validated, bool) or not isinstance(
            self.policy_validated, bool
        ):
            raise ValueError("ProviderReceipt validation flags must be booleans")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PlanningResult:
    plan: ExecutionPlan
    receipt: ProviderReceipt

    def __post_init__(self) -> None:
        if self.receipt.plan_digest != self.plan.digest:
            raise ValueError("Provider receipt is not bound to the execution plan")
        if not self.receipt.schema_validated or not self.receipt.policy_validated:
            raise ValueError("PlanningResult requires schema and policy validation")
        if (
            self.receipt.finish_reason is None
            or self.receipt.finish_reason.casefold() != "stop"
            or not self.receipt.model_version
            or not self.receipt.invocation_id
            or self.receipt.total_tokens is None
        ):
            raise ValueError("PlanningResult requires successful provider evidence")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _exact_mapping(value: Any, expected_fields: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected_fields:
        raise ValueError("Payload fields do not match the versioned contract")
    return value


def task_spec_from_dict(payload: Any) -> TaskSpec:
    """Strictly reconstruct a TaskSpec from packaged JSON."""

    try:
        data = _exact_mapping(
            payload,
            {
                "schema_version",
                "task_id",
                "goal",
                "inputs",
                "allowed_tools",
                "required_deliverables",
                "prohibited_actions",
                "max_plan_steps",
            },
        )
        if not all(
            isinstance(data[name], list)
            for name in (
                "inputs",
                "allowed_tools",
                "required_deliverables",
                "prohibited_actions",
            )
        ):
            raise ValueError("TaskSpec collection fields must be arrays")
        inputs = tuple(
            TaskInputRef(
                **dict(
                    _exact_mapping(
                        item,
                        {"relative_path", "document_type", "source_hash", "size_bytes"},
                    )
                )
            )
            for item in data["inputs"]
        )
        return TaskSpec(
            schema_version=data["schema_version"],
            task_id=data["task_id"],
            goal=data["goal"],
            inputs=inputs,
            allowed_tools=tuple(PlanTool(item) for item in data["allowed_tools"]),
            required_deliverables=tuple(data["required_deliverables"]),
            prohibited_actions=tuple(data["prohibited_actions"]),
            max_plan_steps=data["max_plan_steps"],
        )
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise PlanValidationError(("TASK_SPEC_SCHEMA_INVALID",)) from exc


def execution_plan_from_dict(payload: Any) -> ExecutionPlan:
    """Strictly reconstruct an ExecutionPlan from packaged JSON."""

    try:
        data = _exact_mapping(
            payload,
            {"schema_version", "task_spec_digest", "steps", "summary"},
        )
        if not isinstance(data["steps"], list):
            raise ValueError("ExecutionPlan steps must be an array")
        steps: list[PlanStep] = []
        for item in data["steps"]:
            step = _exact_mapping(
                item,
                {"step_id", "tool", "depends_on", "completion_criterion"},
            )
            if not isinstance(step["depends_on"], list):
                raise ValueError("PlanStep depends_on must be an array")
            steps.append(
                PlanStep(
                    step_id=step["step_id"],
                    tool=PlanTool(step["tool"]),
                    depends_on=tuple(step["depends_on"]),
                    completion_criterion=step["completion_criterion"],
                )
            )
        return ExecutionPlan(
            schema_version=data["schema_version"],
            task_spec_digest=data["task_spec_digest"],
            steps=tuple(steps),
            summary=data["summary"],
        )
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise PlanValidationError(("EXECUTION_PLAN_SCHEMA_INVALID",)) from exc


def provider_receipt_from_dict(payload: Any) -> ProviderReceipt:
    """Strictly reconstruct a ProviderReceipt from packaged JSON."""

    fields = {
        "schema_version",
        "provider",
        "configured_model",
        "model_version",
        "auth_mode",
        "adk_version",
        "genai_version",
        "started_at",
        "duration_ms",
        "event_count",
        "invocation_id",
        "interaction_id",
        "finish_reason",
        "prompt_tokens",
        "output_tokens",
        "total_tokens",
        "request_digest",
        "response_digest",
        "plan_digest",
        "schema_validated",
        "policy_validated",
    }
    try:
        return ProviderReceipt(**dict(_exact_mapping(payload, fields)))
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise PlanValidationError(("PROVIDER_RECEIPT_SCHEMA_INVALID",)) from exc


def validate_planning_evidence(
    task_spec_payload: Any,
    plan_payload: Any,
    receipt_payload: Any,
    *,
    expected_task_id: str | None = None,
) -> tuple[TaskSpec, PlanningResult]:
    """Reparse and verify the packaged task -> plan -> receipt digest chain."""

    task_spec = task_spec_from_dict(task_spec_payload)
    plan = execution_plan_from_dict(plan_payload)
    receipt = provider_receipt_from_dict(receipt_payload)
    if expected_task_id is not None and task_spec.task_id != expected_task_id:
        raise PlanValidationError(("PLANNING_TASK_ID_MISMATCH",))
    validate_execution_plan(plan, task_spec)
    try:
        result = PlanningResult(plan=plan, receipt=receipt)
    except ValueError as exc:
        raise PlanValidationError(("PROVIDER_RECEIPT_BINDING_INVALID",)) from exc
    return task_spec, result


def build_task_spec(task_id: str, documents: tuple[SourceDocument, ...]) -> TaskSpec:
    """Build the only manifest that may be sent to the model planner.

    The source bodies and extracted business facts are deliberately absent.
    """

    inputs = tuple(
        sorted(
            (
                TaskInputRef(
                    relative_path=document.relative_path,
                    document_type=document.document_type.value,
                    source_hash=document.source_hash,
                    size_bytes=document.size_bytes,
                )
                for document in documents
            ),
            key=lambda item: item.relative_path,
        )
    )
    allowed_tools = CANONICAL_TOOL_ORDER
    return TaskSpec(
        task_id=task_id,
        goal=(
            "Generate a traceable tender preparation package from the bounded input manifest. "
            "Preserve unknowns and require deterministic validation before delivery."
        ),
        inputs=inputs,
        allowed_tools=allowed_tools,
        required_deliverables=(
            "requirements.json",
            "evidence.json",
            "result.json",
            "proofbid.xlsx",
            "proofbid_report.docx",
            "trace.jsonl",
            "manifest.json",
            "proofbid_bundle.zip",
            TASK_SPEC_NAME,
            EXECUTION_PLAN_NAME,
            PROVIDER_RECEIPT_NAME,
        ),
        prohibited_actions=(
            "freeze pricing",
            "sign documents",
            "send or submit a bid",
            "access paths outside the bounded workspace",
            "execute shell, arbitrary SQL, arbitrary network, or unregistered tools",
            "invent evidence or replace missing facts",
        ),
        max_plan_steps=len(allowed_tools),
    )


def validate_execution_plan(plan: ExecutionPlan, task_spec: TaskSpec) -> None:
    """Fail closed unless the plan is the complete safe ProofBid DAG."""

    errors: list[str] = []
    if plan.task_spec_digest != task_spec.digest:
        errors.append("TASK_SPEC_DIGEST_MISMATCH")
    if len(plan.steps) > task_spec.max_plan_steps:
        errors.append("PLAN_STEP_LIMIT_EXCEEDED")

    step_ids = [step.step_id for step in plan.steps]
    if len(set(step_ids)) != len(step_ids):
        errors.append("PLAN_STEP_IDS_NOT_UNIQUE")
    tools = [step.tool for step in plan.steps]
    if len(set(tools)) != len(tools):
        errors.append("PLAN_TOOLS_NOT_UNIQUE")
    if set(tools) != set(task_spec.allowed_tools):
        errors.append("PLAN_TOOL_SET_MISMATCH")
    if tuple(tools) != CANONICAL_TOOL_ORDER:
        errors.append("PLAN_TOOL_ORDER_MISMATCH")

    step_by_id = {step.step_id: step for step in plan.steps}
    position = {step.step_id: index for index, step in enumerate(plan.steps)}
    for step in plan.steps:
        if step.step_id in step.depends_on:
            errors.append("PLAN_SELF_DEPENDENCY")
        unknown = [dependency for dependency in step.depends_on if dependency not in step_by_id]
        if unknown:
            errors.append("PLAN_UNKNOWN_DEPENDENCY")
            continue
        if any(position[dependency] >= position[step.step_id] for dependency in step.depends_on):
            errors.append("PLAN_NOT_TOPOLOGICAL")

    step_id_by_tool = {step.tool: step.step_id for step in plan.steps}
    if set(step_id_by_tool) == set(task_spec.allowed_tools):
        for step in plan.steps:
            expected_ids = {
                step_id_by_tool[dependency]
                for dependency in REQUIRED_TOOL_DEPENDENCIES[step.tool]
            }
            if set(step.depends_on) != expected_ids:
                errors.append("PLAN_DEPENDENCY_GRAPH_MISMATCH")
                break

    if errors:
        raise PlanValidationError(tuple(dict.fromkeys(errors)))


def assert_task_inputs_unchanged(
    task_spec: TaskSpec,
    documents: tuple[SourceDocument, ...],
) -> None:
    """Reject execution if any planned input changed before deterministic intake."""

    observed = build_task_spec(task_spec.task_id, documents)
    if observed.inputs != task_spec.inputs:
        raise PlanValidationError(("TASK_INPUT_DRIFT",))


__all__ = [
    "EXECUTION_PLAN_NAME",
    "EXECUTION_PLAN_SCHEMA_VERSION",
    "CANONICAL_TOOL_ORDER",
    "ExecutionPlan",
    "PROVIDER_RECEIPT_NAME",
    "PROVIDER_RECEIPT_SCHEMA_VERSION",
    "PlanStep",
    "PlanTool",
    "PlanValidationError",
    "Planner",
    "PlanningError",
    "PlanningResult",
    "ProviderReceipt",
    "REQUIRED_TOOL_DEPENDENCIES",
    "TASK_SPEC_SCHEMA_VERSION",
    "TASK_SPEC_NAME",
    "TOOL_DESCRIPTIONS",
    "TaskInputRef",
    "TaskSpec",
    "assert_task_inputs_unchanged",
    "build_task_spec",
    "execution_plan_from_dict",
    "provider_receipt_from_dict",
    "task_spec_from_dict",
    "validate_execution_plan",
    "validate_planning_evidence",
]
