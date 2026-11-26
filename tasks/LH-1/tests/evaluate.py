#!/usr/bin/env python3
"""Evaluate submitted geometry with the task's maintained physics programs."""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback


from evaluation_support import CandidateFailure, SubmissionError, validate_boundary


def score(metrics: dict, specification: dict) -> dict:
    # Preserve the native continuous objective/completion score; gates remain diagnostics.
    reference_reward = specification["reference_reward"]
    roundoff_rtol = 1e-12
    objective = specification["objective"]
    components = {}
    for term in specification["terms"]:
        name = term["metric"]
        value = float(metrics[name])
        if not math.isfinite(value):
            raise ValueError(f"The physics calculation returned {name}={value}")
        reference = term["reference"]
        kind = term["kind"]
        if kind == "lower":
            passed = value <= reference or math.isclose(value, reference, rel_tol=roundoff_rtol, abs_tol=0.0)
            floor = term.get("floor", 0.0)
            component = (1.0 if value <= floor else
                         reference_reward * (reference - floor) / (value - floor))
        elif kind == "higher":
            passed = value >= reference or math.isclose(value, reference, rel_tol=roundoff_rtol, abs_tol=0.0)
            component = reference_reward * value / reference
        elif kind == "match":
            distance = abs(value - reference)
            passed = distance <= term["width"] or math.isclose(distance, term["width"], rel_tol=roundoff_rtol, abs_tol=0.0)
            component = 1.0 if distance == 0 else reference_reward * term["width"] / distance
        elif kind == "zero_loss":
            # The published allowance is at most one lost or unresolved orbit.
            passed = term["count"] * value <= 1.0 + roundoff_rtol
            component = 1.0 / (1.0 + term["count"] * value / 9.0)
        else:
            raise ValueError(f"Unknown score definition: {kind}")
        components[name] = {
            "value": value,
            "reference": reference,
            "passed": passed,
            "score": max(0.0, min(1.0, component)),
        }
    completions = []
    for name, item in components.items():
        item["role"] = "objective" if name == objective else "requirement"
        if name != objective:
            completion = min(1.0, item["score"] / reference_reward)
            item["completion"] = completion
            completions.append(completion)
    all_passed = all(item["passed"] for item in components.values())
    return {"reward": components[objective]["score"] * math.prod(completions),
            "legacy_binary_reward": 1.0 if all_passed else 0.0,
            "continuous_score": components[objective]["score"] * math.prod(completions),
            "objective_satisfied": components[objective]["passed"],
            "all_constraints_satisfied": all_passed,
            "objective_metric": objective,
            "requirements_satisfied": all(item["passed"] for name, item in components.items() if name != objective),
            "components": components}


def write_result(output: Path, result: dict) -> None:
    (output / "result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    )
    if "reward" in result:
        (output / "reward.txt").write_text(f"{result['reward']:.17g}\n")
    print(json.dumps({key: result[key] for key in ("status", "reward", "error") if key in result},
                     ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=Path(__file__).with_name("case.json"))
    parser.add_argument("--submission", type=Path, default=Path("/app/boundary.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "reward.txt").unlink(missing_ok=True)
    try:
        case = json.loads(args.case.read_text())
        nfp = case["physics"]["nfp"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        write_result(args.output, {"status": "evaluation_error", "error": str(error)})
        return 1
    try:
        boundary = json.loads(args.submission.read_text(encoding="utf-8"))
    except (FileNotFoundError, IsADirectoryError, ValueError, UnicodeDecodeError, RecursionError) as error:
        write_result(args.output, {"status": "submission_error", "reward": 0.0, "error": str(error)})
        return 0

    try:
        boundary = validate_boundary(boundary, nfp,
                                     allow_duplicates=False, require_origin=True)
    except SubmissionError as error:
        write_result(args.output, {"status": "submission_error", "reward": 0.0, "error": str(error)})
        return 0

    workdir = Path(tempfile.mkdtemp(prefix="physics-", dir=args.output))
    try:
        spec = importlib.util.spec_from_file_location("task_physics", args.case.with_name("physics.py"))
        physics = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = physics
        spec.loader.exec_module(physics)
        result = physics.evaluate(boundary, workdir, case["physics"])
        result.update(score(result["metrics"], case["score"]))
        result["status"] = "ok"
    except CandidateFailure as error:
        (args.output / "error.txt").write_text(traceback.format_exc())
        result = {"status": "physics_failed", "reward": 0.0, "error": str(error)}
    except Exception as error:
        # Includes failed imports and unclassified MPI/native errors. Never assign
        # a candidate zero merely because the evaluator or runtime malfunctioned.
        (args.output / "error.txt").write_text(traceback.format_exc())
        write_result(args.output, {"status": "evaluation_error", "error": str(error),
                                   "physics_directory": str(workdir)})
        return 1
    result["physics_directory"] = str(workdir)
    write_result(args.output, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
