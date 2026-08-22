"""Command-line interface for the local ProofBid vertical slice."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proofbid",
        description="Generate an evidence-backed tender preparation bundle from a synthetic workspace.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="run the deterministic local vertical slice")
    run.add_argument("--workspace", required=True, type=Path, help="isolated input workspace")
    run.add_argument("--output", required=True, type=Path, help="new or empty output directory")
    google_run = subparsers.add_parser(
        "google-run",
        help="plan with Gemini through Google ADK, then run the deterministic pipeline",
    )
    google_run.add_argument(
        "--workspace", required=True, type=Path, help="isolated input workspace"
    )
    google_run.add_argument(
        "--output", required=True, type=Path, help="new or empty output directory"
    )
    google_run.add_argument(
        "--model",
        default=None,
        help="explicit Gemini model id (default: PROOFBID_GEMINI_MODEL or gemini-3.5-flash)",
    )
    agent_run = subparsers.add_parser(
        "agent-run",
        help="run the bounded v2 tool agent with the deterministic local route policy",
    )
    agent_run.add_argument("--workspace", required=True, type=Path)
    agent_run.add_argument("--output", required=True, type=Path)
    agent_run.add_argument("--inject-render-failure", action="store_true")
    google_agent_run = subparsers.add_parser(
        "google-agent-run",
        help="let Gemini route real ADK FunctionTools inside the bounded v2 runtime",
    )
    google_agent_run.add_argument("--workspace", required=True, type=Path)
    google_agent_run.add_argument("--output", required=True, type=Path)
    google_agent_run.add_argument("--model", default=None)
    google_agent_run.add_argument("--inject-render-failure", action="store_true")
    eval_run = subparsers.add_parser(
        "eval",
        help="run the 50-case synthetic local evaluation matrix",
    )
    eval_run.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    from .pipeline import PipelineError, run_pipeline
    from .planning import PlanningError

    try:
        if args.command == "run":
            result = run_pipeline(workspace=args.workspace, output_dir=args.output)
        elif args.command == "google-run":
            from .agent_pipeline import run_google_pipeline

            result = run_google_pipeline(
                workspace=args.workspace,
                output_dir=args.output,
                model=args.model,
            )
        elif args.command == "agent-run":
            from .agent_runtime_v2 import run_scripted_agent_pipeline

            result = run_scripted_agent_pipeline(
                workspace=args.workspace,
                output_dir=args.output,
                inject_render_failure=args.inject_render_failure,
            )
        elif args.command == "google-agent-run":
            from .adapters.google.adk_tool_agent import run_google_tool_agent_pipeline

            result = run_google_tool_agent_pipeline(
                workspace=args.workspace,
                output_dir=args.output,
                model=args.model,
                inject_render_failure=args.inject_render_failure,
            )
        elif args.command == "eval":
            from .evals import run_eval_suite

            result = run_eval_suite(args.output)
        else:
            raise AssertionError(f"Unhandled command: {args.command}")
    except (PipelineError, PlanningError, OSError, ValueError) as exc:
        reason_code = getattr(exc, "reason_code", None)
        payload = {
            "status": "failed",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
        if reason_code:
            payload["reason_code"] = reason_code
        print(
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
