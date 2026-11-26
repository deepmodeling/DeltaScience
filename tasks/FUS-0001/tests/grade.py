"""Independent numerical verifier for the archived MAST-U compatibility task."""
import argparse
import hashlib
import json
import math
from importlib.metadata import version
from pathlib import Path
import numpy as np
from freegs4e import critical
from metric_core import InvalidSubmission, read_submission, evaluate_fields, numerical_result


def trusted_inputs(root):
    """Verify the immutable fixture before reading any candidate data."""
    baseline = json.loads((root / "baseline.json").read_text())
    for package, expected_version in baseline["diagnostic_versions"].items():
        if version(package) != expected_version:
            raise ValueError(f"Diagnostic dependency version mismatch: {package}")
    critical_hash = hashlib.sha256(Path(critical.__file__).read_bytes()).hexdigest()
    if critical_hash != baseline["critical_source_sha256"]:
        raise ValueError("Critical-point diagnostic source mismatch")
    for name, expected_hash in baseline["trusted_files_sha256"].items():
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if actual != expected_hash:
            raise ValueError(f"Trusted fixture mismatch: {name}")
    with np.load(root / "reference.npz", allow_pickle=False) as data:
        reference = {key: data[key] for key in data.files}
    if reference["boundary"].shape != (212, 360, 2):
        raise ValueError("Trusted reference boundary shape mismatch")
    return reference, float(baseline["objective_q95_m"])


def grade(submission, root):
    """Classify bad candidate data separately from trusted evaluator failures."""
    try:
        reference, baseline = trusted_inputs(root)
    except (OSError, ValueError, KeyError, EOFError) as error:
        return {"status": "platform_failure", "fault_layer": "trusted_fixture", "reason": str(error)}
    try:
        fields = read_submission(submission, reference["case_id"])
        rows = evaluate_fields(fields, reference)
    except InvalidSubmission as error:
        return {"status": "invalid_submission", "score": 0., "reason": str(error)}
    return numerical_result(rows, baseline)


def main():
    """Write the numerical receipt and a reward only when a score exists."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = grade(args.submission, Path(__file__).resolve().parent)
    except Exception as error:
        result = {"status": "platform_failure", "fault_layer": "evaluator",
                  "reason": f"{type(error).__name__}: {error}"}
    result["legacy_binary_scoring_version"] = "binary-v1"
    result["binary_threshold"] = 0.4
    continuous = result.get("score")
    if "score" in result:
        if isinstance(continuous, bool) or not isinstance(continuous, (int, float)) or not math.isfinite(continuous) or not 0 <= continuous <= 1:
            result = {"status": "platform_failure", "fault_layer": "evaluator", "reason": "invalid continuous performance score",
                      "legacy_binary_scoring_version": "binary-v1", "binary_threshold": 0.4}
        else:
            result["continuous_score"] = continuous
            result["reward"] = continuous
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "result.json").write_text(json.dumps(result, allow_nan=False, indent=2)+"\n")
    reward = args.output / "reward.txt"
    if "score" in result:
        reward.write_text(str(result["reward"])+"\n")
    elif reward.exists():
        reward.unlink()
    print(json.dumps({key: value for key, value in result.items() if key != "per_case"}))
    return 0 if "reward" in result else 2


if __name__ == "__main__":
    raise SystemExit(main())
