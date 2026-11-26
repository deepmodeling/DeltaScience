from __future__ import annotations

import itertools
import math
from functools import lru_cache

import numpy as np
from scipy import stats


def bh(p: np.ndarray) -> np.ndarray:
    values = np.asarray(p, float)
    out = np.full(len(values), np.nan)
    valid = np.isfinite(values)
    if not valid.any():
        return out
    raw = values[valid]
    order = np.argsort(raw)
    ranked = raw[order]
    adjusted = np.minimum.accumulate((ranked * len(ranked) / np.arange(1, len(ranked) + 1))[::-1])[::-1]
    restored = np.empty_like(adjusted)
    restored[order] = np.minimum(adjusted, 1.0)
    out[valid] = restored
    return out


def holm(p: np.ndarray) -> np.ndarray:
    values = np.asarray(p, float)
    out = np.full(len(values), np.nan)
    valid = np.isfinite(values)
    raw = values[valid]
    order = np.argsort(raw)
    ranked = raw[order]
    adjusted = np.maximum.accumulate((len(ranked) - np.arange(len(ranked))) * ranked)
    restored = np.empty_like(adjusted)
    restored[order] = np.minimum(adjusted, 1.0)
    out[valid] = restored
    return out


def _paired_arrays(rows: list[dict], case_label: str, reference_label: str, value_key: str = "value") -> tuple[np.ndarray, np.ndarray]:
    pairs: dict[str, dict[str, float]] = {}
    for row in rows:
        if not bool(row.get("observable", True)):
            continue
        pair = str(row.get("pair_id", row.get("unit_id", "")))
        pairs.setdefault(pair, {})[str(row["group"])] = float(row[value_key])
    complete = [item for item in pairs.values() if case_label in item and reference_label in item]
    return np.asarray([item[case_label] for item in complete]), np.asarray([item[reference_label] for item in complete])


def _paired_differences(rows: list[dict], case_label: str, reference_label: str, value_key: str = "value") -> np.ndarray:
    by_pair: dict[str, float] = {}
    for row in rows:
        if not bool(row.get("observable", True)) or not is_difference_group(
            row.get("group", ""), case_label, reference_label
        ):
            continue
        pair = str(row.get("pair_id", row.get("unit_id", "")))
        if pair in by_pair:
            return np.asarray([])
        by_pair[pair] = float(row[value_key])
    return np.asarray([by_pair[pair] for pair in sorted(by_pair)], float)


def _independent_arrays(rows: list[dict], case_label: str, reference_label: str, value_key: str = "value") -> tuple[np.ndarray, np.ndarray]:
    case = [float(row[value_key]) for row in rows if bool(row.get("observable", True)) and str(row["group"]) == case_label]
    reference = [float(row[value_key]) for row in rows if bool(row.get("observable", True)) and str(row["group"]) == reference_label]
    return np.asarray(case), np.asarray(reference)


def exact_signflip(diff: np.ndarray) -> tuple[float, float, float]:
    diff = np.asarray(diff, float)
    diff = diff[np.isfinite(diff)]
    if not len(diff):
        return np.nan, np.nan, np.nan
    effect = float(diff.mean())
    signs = np.asarray(list(itertools.product((-1.0, 1.0), repeat=len(diff))))
    null = (signs * diff).mean(axis=1)
    tolerance = 1e-10 * max(1.0, abs(effect))
    p = float(np.mean(np.abs(null) >= abs(effect) - tolerance))
    return effect, effect, p


def exact_label_permutation(case: np.ndarray, reference: np.ndarray) -> tuple[float, float, float]:
    a = np.asarray(case, float); b = np.asarray(reference, float)
    a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
    if not len(a) or not len(b):
        return np.nan, np.nan, np.nan
    pooled = np.r_[a, b]; n_case = len(a); effect = float(a.mean() - b.mean())
    total = math.comb(len(pooled), n_case)
    if total > 200_000:
        raise ValueError("exact label permutation exceeds 200,000 assignments")
    extreme = 0
    for chosen in itertools.combinations(range(len(pooled)), n_case):
        mask = np.zeros(len(pooled), bool); mask[list(chosen)] = True
        permuted = pooled[mask].mean() - pooled[~mask].mean()
        tolerance = 1e-10 * max(1.0, abs(effect))
        extreme += abs(permuted) >= abs(effect) - tolerance
    return effect, effect, float(extreme / total)


def _relationship_arrays(rows: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return predictor, outcome and covariates aligned by independent unit."""
    by_unit: dict[str, dict[str, object]] = {}
    for row in rows:
        if not bool(row.get("observable", True)):
            continue
        role = str(row.get("value_role", ""))
        if role not in {"predictor", "outcome", "covariate"}:
            continue
        unit = str(row.get("unit_id", ""))
        item = by_unit.setdefault(unit, {"predictor": [], "outcome": [], "covariate": {}})
        if role in {"predictor", "outcome"}:
            item[role].append(float(row["value"]))
            continue
        # A covariate column is a scientific variable, not the position of a
        # row in a file.  Key it explicitly so harmless row reordering cannot
        # cause a false rejection and mismatched covariates cannot accidentally
        # reproduce the reference statistic.
        covariate_id = str(
            row.get("feature_id", "")
            or row.get("stratum_id", "")
            or row.get("group", "")
        ).strip()
        if not covariate_id or covariate_id in item["covariate"]:
            return np.asarray([]), np.asarray([]), np.empty((0, 0))
        item["covariate"][covariate_id] = float(row["value"])
    complete = [
        by_unit[unit] for unit in sorted(by_unit)
        if len(by_unit[unit]["predictor"]) == 1 and len(by_unit[unit]["outcome"]) == 1
    ]
    predictor = np.asarray([values["predictor"][0] for values in complete], float)
    outcome = np.asarray([values["outcome"][0] for values in complete], float)
    covariate_sets = [set(values["covariate"]) for values in complete]
    if covariate_sets and any(current != covariate_sets[0] for current in covariate_sets[1:]):
        return np.asarray([]), np.asarray([]), np.empty((0, 0))
    covariate_ids = sorted(covariate_sets[0]) if covariate_sets else []
    covariates = np.asarray(
        [[values["covariate"][name] for name in covariate_ids] for values in complete],
        float,
    ).reshape(len(complete), len(covariate_ids))
    return predictor, outcome, covariates


@lru_cache(maxsize=32)
def _within_block_permutation_indices(blocks: tuple[str, ...], n_permutations: int) -> np.ndarray:
    rng = np.random.default_rng(20261029)
    output = np.tile(np.arange(len(blocks), dtype=np.int16), (n_permutations, 1))
    block_array = np.asarray(blocks, dtype=object)
    for row in range(n_permutations):
        for block in sorted(set(blocks)):
            indices = np.flatnonzero(block_array == block)
            output[row, indices] = rng.permutation(indices)
    return output


@lru_cache(maxsize=16)
def _exact_permutation_orders(size: int) -> np.ndarray:
    """Return positional permutations once per block size.

    The C design reuses the same 6+6 block structure for every prespecified
    relation.  Rebuilding Python tuples and scalar dot products for every
    entity dominated verifier time despite the scientific calculation being
    identical in shape.
    """
    return np.asarray(list(itertools.permutations(range(int(size)))), dtype=np.int16)


def within_block_permutation_correlation(rows: list[dict], n_permutations: int) -> tuple[float, float, float, int]:
    by_unit: dict[str, dict[str, object]] = {}
    for row in rows:
        if not bool(row.get("observable", True)):
            continue
        role = str(row.get("value_role", ""))
        if role not in {"predictor", "outcome"}:
            continue
        unit = str(row.get("unit_id", ""))
        item = by_unit.setdefault(unit, {"block": str(row.get("block_id", ""))})
        item[role] = float(row["value"])
    units = [unit for unit in sorted(by_unit) if "predictor" in by_unit[unit] and "outcome" in by_unit[unit]]
    if len(units) < 3:
        return np.nan, np.nan, np.nan, len(units)
    blocks = tuple(str(by_unit[unit]["block"]) for unit in units)
    if any(not block for block in blocks) or len(set(blocks)) < 2:
        return np.nan, np.nan, np.nan, len(units)
    x = np.asarray([float(by_unit[unit]["predictor"]) for unit in units], float)
    y = np.asarray([float(by_unit[unit]["outcome"]) for unit in units], float)
    block_array = np.asarray(blocks, dtype=object)
    for block in sorted(set(blocks)):
        mask = block_array == block
        x[mask] -= x[mask].mean()
        y[mask] -= y[mask].mean()
    denominator = float(np.sqrt(np.sum(x * x) * np.sum(y * y)))
    if denominator == 0.0:
        return np.nan, np.nan, np.nan, len(units)
    observed = float(y @ x / denominator)
    block_levels = sorted(set(blocks))
    block_indices = [np.flatnonzero(block_array == block) for block in block_levels]
    exact_count = math.prod(math.factorial(len(indices)) for indices in block_indices)
    if int(n_permutations) == exact_count:
        # Enumerate every within-block permutation exactly once.  Combining
        # per-block dot products avoids constructing a 604800 x 12 index
        # matrix for the C reference design.
        block_dots = [
            y[indices][_exact_permutation_orders(len(indices))] @ x[indices]
            for indices in block_indices
        ]
        null_dots = block_dots[0]
        for values in block_dots[1:]:
            null_dots = (null_dots[:, None] + values[None, :]).ravel()
        null = null_dots / denominator
        p_value = float(np.mean(np.abs(null) >= abs(observed) - 1e-12))
    else:
        indices = _within_block_permutation_indices(blocks, int(n_permutations))
        null = (y[indices] @ x) / denominator
        p_value = float((np.sum(np.abs(null) >= abs(observed) - 1e-12) + 1.0) / (len(null) + 1.0))
    return observed, observed, p_value, len(units)


def _correlation_result(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    if len(x) < 3 or len(y) != len(x) or np.std(x) == 0 or np.std(y) == 0:
        return np.nan, np.nan, np.nan
    result = stats.pearsonr(x, y)
    return float(result.statistic), float(result.statistic), float(result.pvalue)


def relationship_correlation(rows: list[dict], adjust_covariates: bool) -> tuple[float, float, float, int]:
    predictor, outcome, covariates = _relationship_arrays(rows)
    if len(predictor) < 3:
        return np.nan, np.nan, np.nan, len(predictor)
    if adjust_covariates and covariates.shape[1] == 0:
        # Without an explicit, consistently keyed covariate this is raw
        # Spearman, not a partial correlation.  Returning a raw result here
        # let a rejected method masquerade as an acceptable fingerprint.
        return np.nan, np.nan, np.nan, 0
    ranked_x = stats.rankdata(predictor)
    ranked_y = stats.rankdata(outcome)
    if adjust_covariates and covariates.shape[1]:
        ranked_covariates = np.column_stack([stats.rankdata(covariates[:, index]) for index in range(covariates.shape[1])])
        design = np.column_stack([np.ones(len(predictor)), ranked_covariates])
        ranked_x = ranked_x - design @ np.linalg.lstsq(design, ranked_x, rcond=None)[0]
        ranked_y = ranked_y - design @ np.linalg.lstsq(design, ranked_y, rcond=None)[0]
    effect, statistic, p_value = _correlation_result(ranked_x, ranked_y)
    return effect, statistic, p_value, len(predictor)


def compute_method(rows: list[dict], spec: dict, method: str) -> dict[str, float]:
    if method in {
        "within_block_permutation",
        "disease_residualized_partial_correlation_with_block_permutation",
    }:
        effect, statistic, p, n_units = within_block_permutation_correlation(
            rows, int(spec.get("n_permutations", 20000))
        )
        return {"effect": effect, "statistic": statistic, "p_value": p,
                "n_case": n_units, "n_reference": n_units}
    if method in {"partial_spearman", "raw_spearman"}:
        effect, statistic, p, n_units = relationship_correlation(rows, method == "partial_spearman")
        return {"effect": effect, "statistic": statistic, "p_value": p,
                "n_case": n_units, "n_reference": n_units}
    paired = bool(spec.get("paired", False))
    case_label = str(spec.get("case_label", "case")); reference_label = str(spec.get("reference_label", "reference"))
    value_key = str(spec.get("value_key", "value"))
    if paired:
        case, reference = _paired_arrays(rows, case_label, reference_label, value_key)
        if not len(case):
            differences = _paired_differences(rows, case_label, reference_label, value_key)
            if len(differences):
                case, reference = differences, np.zeros(len(differences), float)
    else:
        case, reference = _independent_arrays(rows, case_label, reference_label, value_key)
    if method == "paired_signflip":
        effect, statistic, p = exact_signflip(case - reference)
    elif method == "paired_t":
        diff = case - reference; result = stats.ttest_1samp(diff, 0.0)
        effect, statistic, p = float(np.mean(diff)), float(result.statistic), float(result.pvalue)
    elif method == "wilcoxon_signed_rank":
        diff = case - reference; result = stats.wilcoxon(diff, zero_method="wilcox", method="auto")
        effect, statistic, p = float(np.mean(diff)), float(result.statistic), float(result.pvalue)
    elif method == "welch_t":
        result = stats.ttest_ind(case, reference, equal_var=False)
        effect, statistic, p = float(np.mean(case) - np.mean(reference)), float(result.statistic), float(result.pvalue)
    elif method == "mannwhitney":
        result = stats.mannwhitneyu(case, reference, alternative="two-sided")
        effect, statistic, p = float(np.mean(case) - np.mean(reference)), float(result.statistic), float(result.pvalue)
    elif method == "exact_label_permutation":
        effect, statistic, p = exact_label_permutation(case, reference)
    elif method == "unpaired_t_on_paired_values":
        result = stats.ttest_ind(case, reference, equal_var=False)
        effect, statistic, p = float(np.mean(case) - np.mean(reference)), float(result.statistic), float(result.pvalue)
    else:
        raise KeyError(f"unsupported method fingerprint: {method}")
    return {"effect": effect, "statistic": statistic, "p_value": p, "n_case": len(case), "n_reference": len(reference)}


def correction_candidates(p: np.ndarray, submitted_mask: np.ndarray | None = None) -> dict[str, np.ndarray]:
    raw = np.asarray(p, float)
    candidates = {
        "bh_full": bh(raw),
        "bonferroni": np.minimum(raw * np.isfinite(raw).sum(), 1.0),
        "holm": holm(raw),
        "raw_p_as_q": raw.copy(),
        "double_bh": bh(bh(raw)),
    }
    if submitted_mask is not None:
        mask = np.asarray(submitted_mask, bool) & np.isfinite(raw)
        subset = np.full(len(raw), np.nan)
        subset[mask] = bh(raw[mask])
        candidates["bh_submitted_subset"] = subset
        significant = mask & (raw <= 0.05)
        sig = np.full(len(raw), np.nan)
        sig[significant] = bh(raw[significant])
        candidates["bh_significant_subset"] = sig
    return candidates

def is_difference_group(group: object, case_label: object, reference_label: object) -> bool:
    """Recognise a submitted one-row-per-unit case-minus-reference encoding.

    Solvers may retain cohort prefixes (for example PN_L_minus_PN_NL).  The
    terminal arm labels must still match, so an arbitrary one-group table is
    not accepted as a paired difference.
    """
    text = str(group or "").strip().lower().replace("-", "_")
    case = str(case_label or "case").strip().lower().replace("-", "_")
    reference = str(reference_label or "reference").strip().lower().replace("-", "_")
    if text in {f"{case}_{reference}", f"{case}_minus_{reference}",
                "case_reference", "case_minus_reference", "difference"}:
        return True
    if "_minus_" not in text:
        return False
    left, right = text.split("_minus_", 1)
    return (
        (left == case or left.endswith("_" + case))
        and (right == reference or right.endswith("_" + reference))
    )


