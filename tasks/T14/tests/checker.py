from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "reference_resources"))
from replay import Replay


POINTS = {"state.orientation": 2, "state.processing": 2, "state.inventory": 4, "state.budget": 3,
          "state.compatibility": 7, "physics.nominal_replay": 2, "physics.nominal_yield": 16, "mechanism.joint": 64}


def numeric_array(value, length):
    if not isinstance(value, list) or len(value) != length:
        return None
    try:
        if any(isinstance(entry, bool) or not isinstance(entry, (int, float)) or not math.isfinite(entry) for entry in value):
            return None
        return np.array(value, dtype=float)
    except (OverflowError, ValueError, TypeError):
        return None


def curve(deficit, scale):
    ratio = max(0.0, float(deficit)) / scale
    return 1.0 / (1.0 + ratio * ratio)


def grade(data, model, scenarios, trusted_findings=None):
    checks = {name: {"earned": 0.0, "maximum": points, "active": False, "diagnostic": "DEPENDENT_NATIVE_STATE_UNAVAILABLE"}
              for name, points in POINTS.items()}
    observations, integrity_codes, integrity_evidence = {}, [], []
    if not isinstance(data, dict):
        data = {}
    orientation = numeric_array(data.get("orientation"), model["node_count"])
    orientation_valid = orientation is not None and all(type(entry) is int for entry in data["orientation"]) and bool(np.all(np.isin(orientation, (-1.0, 1.0))))
    processing = model["processing"]
    columns = [numeric_array(data.get(field), model["zone_count"]) for field in processing["fields"]]
    controls_valid = all(column is not None for column in columns)
    controls, controls_in_domain = None, False

    def assign(name, quality, diagnostic="PHYSICS_REPLAYED"):
        checks[name] = {"earned": POINTS[name] * float(quality), "maximum": POINTS[name],
                        "active": True, "diagnostic": diagnostic}

    if orientation_valid:
        assign("state.orientation", 1.0, "NATIVE_ORIENTATION_VALID")
        species = np.array(model["chemistry"])
        inventory = [int(np.sum(orientation[species == kind] > 0)) for kind in range(3)]
        inventory_error = np.sqrt(np.mean((np.array(inventory) - 84.0) ** 2))
        assign("state.inventory", curve(inventory_error, 4.0), "INVENTORY_RECOMPUTED")
        observations["positive_inventory"] = inventory
    if controls_valid:
        values = np.column_stack(columns)
        controls = (values - np.array(processing["center"])) / np.array(processing["scale"])
        finite_scaled = np.all(np.isfinite(controls))
        excess = np.maximum(np.abs(controls) - 1.0 - 1e-9, 0.0)
        bounds_quality = float(np.mean(1.0 / (1.0 + np.minimum(excess, 1e100) ** 2 / 0.01))) if finite_scaled else 0.0
        controls_in_domain = finite_scaled and bool(np.all(excess == 0.0))
        assign("state.processing", bounds_quality, "PROCESSING_BOUNDS_RECOMPUTED")
        budget_means = [math.fsum(float(value) / model["zone_count"] for value in column) for column in controls.T] if finite_scaled else [1e100] * 3
        budget_error = math.hypot(*[min(abs(value), 1e100) for value in budget_means]) / np.sqrt(3.0)
        assign("state.budget", curve(max(0.0, budget_error - 1e-9), 0.03), "PROCESSING_BUDGET_RECOMPUTED")
        observations["normalized_budget_rms"] = float(budget_error)
    physics_available = orientation_valid and controls_in_domain
    if physics_available:
        physics = Replay(model).evaluate(orientation, controls, scenarios)
        observations.update(physics)
        incompatibility = math.hypot(physics["compatibility_fraction"] / 0.035, physics["process_rms"] / 0.12)
        assign("state.compatibility", curve(incompatibility, 1.0))
        assign("physics.nominal_replay", curve(0.985 - physics["nominal_weakest"], 0.24))
        assign("physics.nominal_yield", curve(0.985 - physics["nominal_mean"], 0.30))
        assign("mechanism.joint", curve(0.960 - physics["joint_weakest"], 0.18))
    claim_names = {"joint_weakest_yield", "release_yield", "observables", "reported_results"}
    if claim_names.intersection(data) and not (orientation_valid or controls_valid):
        integrity_codes.append("GUESS_ONLY_SUBMISSION")
        integrity_evidence.append({"source": "checker-side required-native-state inventory", "observation": "Scientific assertions with no minimally valid required native state"})
    permitted_codes = {"PROHIBITED_INPUT_ACCESS", "EVALUATOR_OR_INPUT_TAMPERING", "PROVEN_CROSS_ARM_COPYING", "FABRICATED_EXECUTION_PROVENANCE"}
    for finding in trusted_findings or []:
        if finding.get("code") in permitted_codes and finding.get("source") and finding.get("observation"):
            integrity_codes.append(finding["code"])
            integrity_evidence.append(finding)
    scientific_raw_points = math.fsum(check["earned"] for check in checks.values())
    integrity_status = "INTEGRITY_DISQUALIFIED" if integrity_codes else "INTEGRITY_PASS"
    final_points = 0.0 if integrity_codes else scientific_raw_points
    return {"reward": final_points / 100.0, "final_points": final_points, "scientific_raw_points": scientific_raw_points,
            "integrity_status": integrity_status, "integrity_codes": integrity_codes, "integrity_evidence": integrity_evidence,
            "checks": checks, "observations": observations}


def load_submission(outputs):
    if outputs.is_symlink():
        return {}, "OUTPUT_ROOT_SYMLINK"
    path = outputs / "design.json"
    total_size = 0
    if outputs.exists():
        for directory, _, filenames in os.walk(outputs, followlinks=False):
            for filename in filenames:
                member = Path(directory) / filename
                if member.is_symlink():
                    continue
                total_size += member.stat().st_size
                if total_size > 2 * 1024 * 1024:
                    return {}, "OUTPUT_SIZE_LIMIT_EXCEEDED"
    if not path.is_file() or path.is_symlink():
        return {}, "REQUIRED_NATIVE_STATE_MISSING"
    try:
        directory_descriptor = os.open(outputs, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            descriptor = os.open("design.json", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_descriptor)
            with os.fdopen(descriptor, "rb") as stream:
                payload = stream.read(2 * 1024 * 1024 + 1)
            if len(payload) > 2 * 1024 * 1024:
                return {}, "OUTPUT_SIZE_LIMIT_EXCEEDED"
            return json.loads(payload), "SUBMISSION_READ"
        finally:
            os.close(directory_descriptor)
    except (OSError, UnicodeError, ValueError, RecursionError):
        return {}, "NATIVE_STATE_UNREADABLE"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resources", type=Path, default=Path("/workspace/resources"))
    parser.add_argument("--outputs", type=Path, default=Path("/workspace/outputs"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--trusted-findings", type=Path)
    args = parser.parse_args()
    bindings = json.loads((HERE / "reference_resources/bindings.json").read_text())
    verified_resources = {}
    for filename, expected in bindings.items():
        payload = (args.resources / filename).read_bytes()
        actual = hashlib.sha256(payload).hexdigest()
        if actual != expected:
            raise RuntimeError("PACKAGE_CONTRACT_FAILURE: registered input digest mismatch")
        verified_resources[filename] = payload
    model = json.loads(verified_resources["network.json"])
    scenarios = json.loads((HERE / "reference_resources/scenarios.json").read_text())
    findings = json.loads(args.trusted_findings.read_text()) if args.trusted_findings else []
    submission, read_diagnostic = load_submission(args.outputs)
    result = grade(submission, model, scenarios, findings)
    result["submission_diagnostic"] = read_diagnostic
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, allow_nan=False) + "\n")
    print(json.dumps({"final_points": result["final_points"], "integrity_status": result["integrity_status"]}))


if __name__ == "__main__":
    main()
