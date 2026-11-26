"""Paper-bound field evaluation; contains no submission-code execution."""
from pathlib import Path
import zipfile
import numpy as np
from paper_geometry import Separatrix, max_euclidean_distance


FULL_SCORE_Q95_M = 0.03
SCORING_VERSION = "mastu-q95-30mm-v1"


class InvalidSubmission(ValueError):
    """The submitted data do not define all required numerical results."""


def read_submission(path, expected_ids):
    """Read a bounded, data-only NPZ and align its rows to trusted case IDs."""
    if not Path(path).is_file():
        raise InvalidSubmission("Missing flux.npz")
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) != 2 or sum(m.file_size for m in members) > 32_000_000:
                raise InvalidSubmission("NPZ must have exactly two bounded data arrays")
        with np.load(path, allow_pickle=False) as data:
            if set(data.files) != {"case_id", "psi_Wb"}:
                raise InvalidSubmission("Expected only case_id and psi_Wb")
            case_ids, fields = data["case_id"], data["psi_Wb"]
    except (OSError, ValueError, zipfile.BadZipFile, EOFError) as error:
        raise InvalidSubmission(f"Cannot read data-only NPZ: {error}") from error
    if case_ids.dtype.kind != "U" or case_ids.shape != expected_ids.shape:
        raise InvalidSubmission("case_id must be a complete Unicode vector")
    names = case_ids.tolist()
    if len(set(names)) != len(names) or set(names) != set(expected_ids.tolist()):
        raise InvalidSubmission("Missing, duplicate, or unexpected case IDs")
    if fields.shape != (len(names), 65, 65) or fields.dtype.kind != "f":
        raise InvalidSubmission("psi_Wb must be floating point with shape (212,65,65)")
    if not np.isfinite(fields).all():
        raise InvalidSubmission("Nonfinite submitted flux")
    positions = {name: i for i, name in enumerate(names)}
    return fields[[positions[name] for name in expected_ids.tolist()]]


def evaluate_fields(fields, reference):
    """Apply the published contour diagnostic to every required flux field."""
    R, Z = np.meshgrid(np.linspace(.06, 2., 65), np.linspace(-2.2, 2.2, 65), indexing="ij")
    rows = []
    for i, name in enumerate(reference["case_id"].tolist()):
        try:
            predicted, _ = Separatrix(R, Z, fields[i], ntheta=360,
                                      input_opoint=reference["magnetic_axis"][i])
            boundary = reference["boundary"][i]
            distance = float(max_euclidean_distance(predicted, boundary))
        except (IndexError, ValueError, FloatingPointError) as error:
            raise InvalidSubmission(f"Cannot extract boundary for {name}: {error}") from error
        if not np.isfinite(distance):
            raise InvalidSubmission(f"No finite paper boundary metric for {name}")
        valid = np.all(np.isfinite(predicted), axis=1) & np.all(np.isfinite(boundary), axis=1)
        rows.append({"case_id": name, "zeta_m": distance, "valid_directions": int(valid.sum())})
    return rows


def numerical_result(rows, baseline):
    """Return raw geometric improvement, independent of all trace judgments."""
    errors = np.asarray([row["zeta_m"] for row in rows])
    if len(errors) != 212 or not np.isfinite(errors).all() or np.any(errors < 0):
        raise ValueError("Scorer requires 212 finite nonnegative distances")
    if not np.isfinite(baseline) or not FULL_SCORE_Q95_M < baseline < 0.05:
        raise ValueError("Trusted baseline must lie strictly between the 0.03 m full-score and 0.05 m zero-score anchors")
    objective = float(np.quantile(errors, .95, method="linear"))
    improvement = 1 - objective / baseline
    score = (0.2 + 0.8 * (baseline - objective) / (baseline - FULL_SCORE_Q95_M) if objective <= baseline
             else 0.2 * (0.05 - objective) / (0.05 - baseline))
    return {"status": "scored", "score": float(np.clip(score, 0, 1)),
            "objective_q95_m": objective, "baseline_q95_m": float(baseline),
            "full_score_q95_m": FULL_SCORE_Q95_M, "scoring_version": SCORING_VERSION,
            "relative_improvement": float(improvement),
            "fraction_zeta_below_035": float(np.mean(errors < .035)), "per_case": rows}
