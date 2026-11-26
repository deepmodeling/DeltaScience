from __future__ import annotations

import hashlib
import math

import numpy as np

from .models import AtomDefinition, AtomScore
from .statistics import compute_method, correction_candidates, is_difference_group


_METHOD_ALIASES = {
    "paired_signflip": ("paired sign flip", "paired signflip", "sign flip", "signflip"),
    "paired_t": (
        "paired t", "paired t test", "paired ttest",
        "paired patient t test", "paired patient ttest",
    ),
    "wilcoxon_signed_rank": ("wilcoxon signed rank", "signed rank"),
    "unpaired_t_on_paired_values": (
        "unpaired t", "unpaired patient t test", "independent patient t test",
        "independent t on paired values", "unpaired t on paired values",
    ),
    "exact_label_permutation": ("exact label permutation", "label permutation", "permutation test"),
    "welch_t": ("welch t", "welch t test", "welch ttest"),
    "mannwhitney": ("mann whitney", "mannwhitney", "rank sum", "ranksum"),
    "partial_spearman": ("partial spearman", "spearman partial"),
    "pearson_partial": ("partial pearson", "pearson partial"),
    "disease_residualized_partial_correlation_with_block_permutation": (
        "disease residualized partial correlation with block permutation",
        "disease residualised partial correlation with block permutation",
        "residualized block permutation",
    ),
}


def _evidence_semantic_text(row: dict) -> str:
    """Expose the analysed endpoint, not only the solver's display label.

    Legitimate evidence often stores the biological endpoint in feature_id or
    stratum_id and the treatment/contrast in group.  Result binding therefore
    sees all endpoint-defining fields while statistical eligibility continues
    to be decided independently.
    """
    values = [
        row.get("entity_id", ""),
        *row.get("semantic_aliases", []),
        row.get("feature_id", ""),
        row.get("stratum_id", ""),
    ]
    unique: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in unique:
            unique.append(text)
    return " | ".join(unique)


def _normalise_method_declaration(value: object, candidates: set[str]) -> set[str]:
    """Map free-form method prose to known codes without making prose a gate.

    Numeric fingerprints remain authoritative.  This parser is used only to
    catch an explicit declaration of a known rejected method or to report a
    recognised acceptable declaration.
    """
    text = " ".join(str(value).strip().lower().replace("_", " ").replace("-", " ").split())
    matched: set[str] = set()
    for code in candidates:
        code_text = " ".join(code.lower().replace("_", " ").split())
        phrases = {
            " ".join(phrase.lower().replace("_", " ").replace("-", " ").split())
            for phrase in (code_text, *_METHOD_ALIASES.get(code, ()))
        }
        if any(phrase in text for phrase in phrases):
            matched.add(code)
    return matched


def _log_distance(observed: float, expected: float) -> float:
    if not math.isfinite(observed) or not math.isfinite(expected):
        return 50.0
    return abs(-math.log10(max(observed, 1e-300)) + math.log10(max(expected, 1e-300)))


def _finite_number(value: object) -> float | None:
    """Return a finite float, or None for a submitted missing/invalid value.

    A malformed numeric cell is model evidence failure, not verifier failure.
    Callers assign a large distance so it cannot accidentally strengthen a
    method or BH fingerprint.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _numeric_distance_profile(
    reported: list[dict], computed: dict[str, dict[str, float]]
) -> dict[str, float]:
    distances: dict[str, float] = {}
    by_entity = {str(row["entity_id"]): row for row in reported}
    for entity_id, expected in computed.items():
        row = by_entity.get(entity_id)
        if row is None or not bool(row.get("observable", True)):
            continue
        if not np.isfinite(float(expected.get("p_value", np.nan))):
            continue
        observed_p = _finite_number(row.get("p_value"))
        expected_p = _finite_number(expected.get("p_value"))
        observed_effect = _finite_number(row.get("effect"))
        expected_effect = _finite_number(expected.get("effect"))
        if observed_p is None or expected_p is None or observed_effect is None or expected_effect is None:
            distances[entity_id] = 50.0
            continue
        p_distance = _log_distance(observed_p, expected_p)
        effect_scale = max(1.0, abs(expected_effect))
        effect_distance = abs(observed_effect - expected_effect) / effect_scale
        expected_statistic = _finite_number(expected.get("statistic"))
        reported_statistic = _finite_number(row.get("statistic"))
        expected_statistic = expected_statistic if expected_statistic is not None else np.nan
        reported_statistic = reported_statistic if reported_statistic is not None else np.nan
        statistic_scale = max(1.0, abs(expected_statistic)) if np.isfinite(expected_statistic) else 1.0
        statistic_distance = abs(reported_statistic - expected_statistic) / statistic_scale if np.isfinite(reported_statistic) and np.isfinite(expected_statistic) else 0.0
        distances[entity_id] = p_distance + 0.25 * effect_distance + 0.10 * statistic_distance
    return distances


def _numeric_distance(reported: list[dict], computed: dict[str, dict[str, float]]) -> float:
    distances = list(_numeric_distance_profile(reported, computed).values())
    # A deterministic fingerprint is a full pass only when every audited
    # entity is compatible.  Entity-local partial credit is handled separately
    # by ``method_match_fraction``; an aggregate quantile must not hide a
    # corrupted tail and label the whole method as confirmed.
    return float(np.max(distances)) if distances else float("inf")


def _q_distance_profile(
    reported: list[dict], entities: list[str], expected_q: np.ndarray
) -> dict[str, float]:
    by_entity = {str(row["entity_id"]): row for row in reported}
    distances: dict[str, float] = {}
    for entity_id, q_value in zip(entities, expected_q):
        row = by_entity.get(entity_id)
        if row is None or not bool(row.get("observable", True)) or not np.isfinite(q_value):
            continue
        observed_q = _finite_number(row.get("q_value"))
        expected_q_value = _finite_number(q_value)
        distances[entity_id] = (
            50.0 if observed_q is None or expected_q_value is None
            else _log_distance(observed_q, expected_q_value)
        )
    return distances


def _q_distance(reported: list[dict], entities: list[str], expected_q: np.ndarray) -> float:
    distances = list(_q_distance_profile(reported, entities, expected_q).values())
    # BH is deterministic conditional on the submitted raw-P family.  Every
    # observable family member must therefore be compatible; an average or
    # median would allow a partly corrected family to pass.
    return float(np.max(distances)) if distances else float("inf")


def _infer(
    best_scores: dict[str, float],
    acceptable_codes: set[str],
    ambiguity_margin: float,
    maximum_match_distance: float,
) -> tuple[str, str, float, float]:
    ordered = sorted(best_scores.items(), key=lambda item: item[1])
    if not ordered or not np.isfinite(ordered[0][1]):
        return "insufficient_process_data", "", float("inf"), float("inf")
    best_name, best = ordered[0]
    second = ordered[1][1] if len(ordered) > 1 else float("inf")
    near_best = {name for name, distance in ordered if distance - best <= ambiguity_margin}
    if best > maximum_match_distance:
        status = "inconsistent_or_unrecognized"
    elif best_name in acceptable_codes:
        status = "confirmed_acceptable_method"
    elif near_best & acceptable_codes:
        status = "ambiguous_with_acceptable_method"
    else:
        status = f"likely_rejected_method:{best_name}"
    return status, best_name, best, second


def _method_policy(spec: dict) -> tuple[list[str], set[str], set[str]]:
    """Return all fingerprints, acceptable methods, and explicitly rejected methods."""
    reference = str(spec["reference_method"])
    alternatives = [str(value) for value in spec.get("alternative_methods", [])]
    if spec.get("acceptable_methods"):
        acceptable = {reference, *(str(value) for value in spec["acceptable_methods"])}
    elif reference == "paired_signflip":
        acceptable = {"paired_signflip", "paired_t", "wilcoxon_signed_rank"}
    elif reference == "exact_label_permutation":
        acceptable = {"exact_label_permutation", "welch_t", "mannwhitney"}
    else:
        # Relationship methods that encode covariate or block control are not
        # interchangeable with the unadjusted alternatives in the reference.
        acceptable = {reference}
    rejected = set(map(str, spec.get("rejected_methods", [])))
    # For paired patient-level questions, the most consequential competing
    # fingerprint is an unpaired analysis of the same values.  It is not a
    # scientifically acceptable alternative and must be present in the
    # comparison set; otherwise a numerically similar unpaired result can be
    # mistaken for a valid paired test.
    if bool(spec.get("paired", False)):
        rejected.add("unpaired_t_on_paired_values")
    if not rejected:
        rejected = {reference, *alternatives} - acceptable
    candidates = list(dict.fromkeys([reference, *alternatives, *sorted(acceptable), *sorted(rejected)]))
    return candidates, acceptable, rejected


def _family_signature(component_id: str, entity_id: object) -> str:
    """Canonical scientific member key, excluding solver-defined scope labels."""
    text = str(entity_id).strip()
    text = text.replace("MSigDB_Hallmark_2020.gmt", "Hallmark_2020")
    text = text.replace("MSigDB_Hallmark_2020", "Hallmark_2020")
    text = text.replace("GO_Biological_Process_2023.gmt", "GO_BP_2023")
    text = text.replace("GO_Biological_Process_2023", "GO_BP_2023")
    text = text.replace("Reactome_2022.gmt", "Reactome_2022")
    parts = [part.strip().upper() for part in text.split("|") if part.strip()]
    if component_id.startswith("pathway__") and len(parts) >= 2:
        return "|".join(parts[-2:])
    if component_id.startswith("communication__") and len(parts) >= 3:
        # Receiver/family scope is already fixed by the submitted family key,
        # but the source node is part of the tested communication hypothesis.
        # Dropping it collapsed 695 A relations to 319 ligand-receptor pairs
        # and allowed a source-incomplete family to masquerade as complete.
        return "|".join(parts[-3:])
    if component_id.startswith("tf_coupling__") and len(parts) >= 2:
        return "|".join(parts[-2:])
    if component_id.startswith("tf") and parts:
        return parts[-1]
    return "|".join(parts)


def _validate_family_signatures(
    component_id: str,
    spec: dict,
    entities: list[str],
) -> tuple[bool, dict[str, object]]:
    """Validate a complete analysis family without freezing variable outputs.

    A fixed public universe is exact.  For HIGH/MODERATE analysis families,
    the preexperiment is a reference core rather than the only legal output:
    bounded reference coverage and bounded additional members distinguish a
    complete equivalent family from a cherry-picked or sprayed family.
    """
    properties = set(map(str, spec.get("required_design_properties", [])))
    if not properties.intersection({
        "complete_library", "complete_regulon_family", "declared_family_multiplicity",
    }):
        return True, {"required": False}
    expected = {
        _family_signature(component_id, value)
        for value in spec.get("family_entities", []) if str(value).strip()
    }
    submitted = {
        _family_signature(component_id, value) for value in entities if str(value).strip()
    }
    mode = str(spec.get("family_validation_mode", ""))
    if mode == "compact_resource_family":
        # Dynamic data-dependent families must not be compared with the full
        # member list from one preexperiment.  Validate a bounded deterministic
        # audit core when a stable public universe is available; otherwise
        # validate only structured, non-empty audit evidence here.  Full-family
        # size and multiplicity are handled by the compact family manifest.
        audit_maximum = int(spec.get("compact_audit_maximum", 64))
        expected_audit = set(sorted(
            expected,
            key=lambda value: hashlib.sha256(
                f"{spec.get('match_stage', '')}|{component_id}|{value}".encode("utf-8")
            ).hexdigest(),
        )[:audit_maximum])
        is_communication = component_id.startswith("communication__")
        minimum_overlap = int(spec.get(
            "minimum_compact_audit_overlap",
            0 if is_communication or not expected_audit else min(8, len(expected_audit)),
        ))
        overlap = len(expected_audit & submitted)
        minimum_rows = int(spec.get("minimum_compact_audit_rows", 8))
        structured = {
            value for value in submitted
            if value and (
                not is_communication
                or len([part for part in value.split("|") if part]) >= 3
            )
        }
        required_rows = min(minimum_rows, len(expected_audit)) if expected_audit else minimum_rows
        valid = bool(submitted) and len(structured) >= required_rows
        if minimum_overlap:
            valid = valid and overlap >= minimum_overlap
        return valid, {
            "required": True,
            "policy": "compact_resource_family_audit",
            "answer_variability": str(spec.get("answer_variability", "LOW")).upper(),
            "reference_pool_is_exhaustive": False,
            "submitted_audit_members": len(submitted),
            "structured_audit_members": len(structured),
            "minimum_audit_rows": required_rows,
            "expected_audit_members": len(expected_audit),
            "reference_audit_overlap": overlap,
            "minimum_reference_audit_overlap": minimum_overlap,
            "full_reference_members_not_required": True,
        }

    missing = expected - submitted
    unexpected = submitted - expected
    variability = str(spec.get("answer_variability", "LOW")).upper()
    exact = bool(spec.get("fixed_public_universe", False)) or variability == "LOW"
    defaults = {
        "MODERATE": (0.85, 0.20),
        "HIGH": (0.75, 0.30),
    }
    minimum_coverage, maximum_unexpected = defaults.get(variability, (1.0, 0.0))
    minimum_coverage = float(spec.get("minimum_reference_family_coverage", minimum_coverage))
    maximum_unexpected = float(spec.get("maximum_unexpected_family_fraction", maximum_unexpected))
    coverage = len(expected & submitted) / len(expected) if expected else 1.0
    unexpected_fraction = len(unexpected) / len(submitted) if submitted else (1.0 if expected else 0.0)
    valid = bool(submitted) and (
        (not missing and not unexpected)
        if exact else (
            coverage + 1e-12 >= minimum_coverage
            and unexpected_fraction <= maximum_unexpected + 1e-12
        )
    )
    return valid, {
        "required": True,
        "policy": "exact" if exact else "bounded_equivalent_family",
        "answer_variability": variability,
        "expected_family_members": len(expected),
        "submitted_family_members": len(submitted),
        "reference_coverage": coverage,
        "minimum_reference_coverage": minimum_coverage,
        "unexpected_fraction": unexpected_fraction,
        "maximum_unexpected_fraction": maximum_unexpected,
        "missing_reference_family_members": sorted(missing),
        "unexpected_family_members": sorted(unexpected),
    }


def _validate_reported_family(
    reported: list[dict],
    entities: list[str],
    require_inference: bool = True,
    required_numeric_fields: tuple[str, ...] | None = None,
) -> tuple[bool, dict[str, object]]:
    required_numeric = required_numeric_fields or (
        ("effect", "statistic", "p_value", "q_value")
        if require_inference else ("effect",)
    )
    by_entity: dict[str, list[dict]] = {}
    for row in reported:
        by_entity.setdefault(str(row.get("entity_id", "")), []).append(row)
    missing_entities = [entity for entity in entities if entity not in by_entity]
    duplicate_entities = [entity for entity, rows in by_entity.items() if entity in entities and len(rows) != 1]
    invalid_fields: list[str] = []
    nonobservable_entities: list[str] = []
    for entity in entities:
        rows = by_entity.get(entity, [])
        if len(rows) != 1:
            continue
        if not bool(rows[0].get("observable", True)):
            nonobservable_entities.append(entity)
            continue
        for field in required_numeric:
            try:
                value = float(rows[0][field])
            except (KeyError, TypeError, ValueError):
                invalid_fields.append(f"{entity}:{field}")
                continue
            if not np.isfinite(value):
                invalid_fields.append(f"{entity}:{field}")
            elif field in ("p_value", "q_value") and not 0.0 <= value <= 1.0:
                invalid_fields.append(f"{entity}:{field}")
    valid = not missing_entities and not duplicate_entities and not invalid_fields
    return valid, {
        "missing_entities": missing_entities,
        "duplicate_entities": duplicate_entities,
        "invalid_fields": invalid_fields,
        "nonobservable_entities": nonobservable_entities,
    }


def _canonicalise_observation_units(
    observations: list[dict], unit_contract: dict | None
) -> list[dict]:
    """Apply only one-to-one aliases explicitly frozen in the private map.

    C has one sample per patient, so C_Sxx and C_Pxx are the same independent
    unit.  A/B do not have this property and therefore intentionally expose no
    sample aliases.  This avoids rejecting a scientifically identical C
    analysis merely because it retained sample IDs from the public metadata.
    """
    aliases = {
        str(source): str(target)
        for source, target in (unit_contract or {}).get("unit_aliases", {}).items()
    }
    if not aliases:
        return observations
    canonical: list[dict] = []
    for row in observations:
        copy = dict(row)
        unit = str(copy.get("unit_id", "")).strip()
        pair = str(copy.get("pair_id", "")).strip()
        if unit in aliases:
            copy["unit_id"] = aliases[unit]
        if pair in aliases:
            copy["pair_id"] = aliases[pair]
        canonical.append(copy)
    return canonical


def _validate_design(
    observations: list[dict],
    entities: list[str],
    spec: dict,
    nonobservable_entities: set[str] | None = None,
    unit_contract: dict | None = None,
) -> tuple[bool, dict[str, object]]:
    design_type = str(spec.get("design_type", "group_contrast"))
    expected_groups = {str(spec.get("case_label", "case")), str(spec.get("reference_label", "reference"))}
    requirements = set(map(str, spec.get("design_requirements", [])))
    nonobservable_entities = nonobservable_entities or set()
    unit_contract = unit_contract or {}
    allowed_units = set(map(str, unit_contract.get("units", [])))
    group_membership = {
        str(group): set(map(str, units))
        for group, units in unit_contract.get("group_membership", {}).items()
    }
    unit_groups: dict[str, set[str]] = {}
    for group, units in group_membership.items():
        for unit in units:
            unit_groups.setdefault(unit, set()).add(group)
    acquisition_value_map = {
        str(unit): float(value)
        for unit, value in unit_contract.get("acquisition_value_map", {}).items()
    }
    paired = bool(spec.get("paired", False)); min_pairs = int(spec.get("min_pairs", 2)); reasons = []
    observations_by_entity: dict[str, list[dict]] = {}
    for row in observations:
        observations_by_entity.setdefault(str(row.get("entity_id", "")), []).append(row)
    seen = set(); duplicates = 0; duplicate_entities: set[str] = set()
    for row in observations:
        key = (str(row.get("entity_id")), str(row.get("unit_id")), str(row.get("group")),
               str(row.get("value_role", "")), str(row.get("feature_id", "")), str(row.get("stratum_id", "")),
               str(row.get("block_id", "")), str(row.get("time", "")))
        if key in seen:
            duplicates += 1
            duplicate_entities.add(str(row.get("entity_id", "")))
        seen.add(key)
    pair_counts = {}
    for entity in entities:
        entity_rows = observations_by_entity.get(entity, [])
        rows = [row for row in entity_rows if bool(row.get("observable", True))]
        analysis_rows = [
            row for row in rows
            if str(row.get("value_role", "")) not in {"predictor_member", "outcome_member"}
        ]
        expected_prefix = str(spec.get("entity_prefix", "")).strip()
        expected_parts = int(spec.get("entity_part_count", 0) or 0)
        parts = entity.split("|")
        if expected_prefix and (not parts or parts[0] != expected_prefix):
            reasons.append(f"{entity}: entity prefix does not identify the declared scientific component")
        if expected_parts and len(parts) != expected_parts:
            reasons.append(f"{entity}: entity structure has {len(parts)} parts, expected {expected_parts}")

        # A declared non-observable family member remains in the multiplicity
        # family but has no estimable unit-level vector.  It must bypass the
        # design-specific row-count checks; observability legitimacy is
        # validated separately against the fixed or bounded reference core.
        if entity in nonobservable_entities:
            pair_counts[entity] = 0
            continue

        if design_type == "identifiability_audit":
            groups: dict[str, list[float]] = {}
            acquisition_rows = [
                row for row in analysis_rows
                if str(row.get("value_role", "")) == "covariate"
                and str(row.get("feature_id", "")) == "acquisition_order"
            ]
            audit_rows = acquisition_rows or analysis_rows
            observed_units = {str(row.get("unit_id", "")) for row in audit_rows}
            if allowed_units:
                unknown_units = sorted(observed_units - allowed_units)
                if unknown_units:
                    reasons.append(f"{entity}: units outside private sample map: {unknown_units[:5]}")
            for row in audit_rows:
                # Public E submissions may carry acquisition order in `time`
                # while `value` remains the protein abundance and `block_id`
                # remains the acquisition batch.  The older audit-only form
                # used the order in both value and block_id.  The current
                # contract also permits an explicit acquisition-order
                # covariate row.  All three expose the same independently
                # verifiable sample-order design.
                if acquisition_rows:
                    order_source = row.get("value", "")
                else:
                    order_source = row.get("time", "")
                    if order_source in {"", None}:
                        order_source = row.get("block_id", "")
                try:
                    order_value = float(order_source)
                except (TypeError, ValueError):
                    reasons.append(f"{entity}: acquisition-order value is not numeric")
                    continue
                if not np.isfinite(order_value):
                    reasons.append(f"{entity}: acquisition-order value is not finite")
                    continue
                unit = str(row.get("unit_id", ""))
                group = str(row.get("group", ""))
                if acquisition_value_map:
                    expected_value = acquisition_value_map.get(unit)
                    if expected_value is None or order_value != expected_value:
                        reasons.append(f"{entity}: acquisition order for {unit} does not match the private sample map")
                        continue
                if group in group_membership and unit not in group_membership[group]:
                    reasons.append(f"{entity}: unit {unit} is not mapped to group {group}")
                    continue
                groups.setdefault(group, []).append(order_value)
            minimum = int(spec.get("minimum_units_per_group", 2))
            if set(groups) != expected_groups or any(len(groups.get(group, [])) < minimum for group in expected_groups):
                reasons.append(f"{entity}: acquisition audit lacks the required groups or units")
            else:
                first, second = sorted(expected_groups)
                identifiable = not (
                    max(groups[first]) < min(groups[second])
                    or max(groups[second]) < min(groups[first])
                )
                if identifiable != bool(spec.get("expected_identifiable", True)):
                    reasons.append(f"{entity}: acquisition identifiability status is inconsistent with submitted order values")
            pair_counts[entity] = len(observed_units)
            continue

        if design_type == "gene_set_enrichment":
            # The submission contract exposes the structured enrichment
            # family and its provenance identifiers, not the complete ranked
            # gene vector.  Validate only what is genuinely observable here;
            # endpoint identity/direction is scored in the result atom.
            features = {
                str(row.get("feature_id", "")).strip()
                or str(row.get("entity_id", "")).strip()
                for row in analysis_rows
                if str(row.get("feature_id", "")).strip()
                or str(row.get("entity_id", "")).strip()
            }
            strata = {
                str(row.get("stratum_id", "")).strip()
                for row in analysis_rows if str(row.get("stratum_id", "")).strip()
            }
            if len(analysis_rows) < int(spec.get("minimum_summary_rows", 1)):
                reasons.append(f"{entity}: enrichment family has too few structured rows")
            if len(features) < int(spec.get("minimum_feature_levels", 1)):
                reasons.append(f"{entity}: enrichment family lacks feature identifiers")
            if len(strata) < int(spec.get("minimum_stratum_levels", 1)):
                reasons.append(f"{entity}: enrichment family lacks library/state strata")
            for row in analysis_rows:
                try:
                    value = float(row.get("value", ""))
                except (TypeError, ValueError):
                    reasons.append(f"{entity}: enrichment summary value is not numeric")
                    continue
                if not np.isfinite(value):
                    reasons.append(f"{entity}: enrichment summary value is not finite")
            pair_counts[entity] = len(analysis_rows)
            continue

        if design_type == "sensitivity_summary":
            units = {str(row.get("unit_id", "")).strip() for row in analysis_rows if str(row.get("unit_id", "")).strip()}
            features = {str(row.get("feature_id", "")).strip() for row in analysis_rows if str(row.get("feature_id", "")).strip()}
            blocks = {str(row.get("block_id", "")).strip() for row in analysis_rows if str(row.get("block_id", "")).strip()}
            strata = {str(row.get("stratum_id", "")).strip() for row in analysis_rows if str(row.get("stratum_id", "")).strip()}
            if len(units) < int(spec.get("minimum_unit_levels", 1)):
                reasons.append(f"{entity}: too few independently omitted units")
            if len(features) < int(spec.get("minimum_feature_levels", 0)):
                reasons.append(f"{entity}: too few distinct omitted features")
            if len(blocks) < int(spec.get("minimum_block_levels", 0)):
                reasons.append(f"{entity}: too few distinct omitted blocks")
            if len(strata) < int(spec.get("minimum_stratum_levels", 0)):
                reasons.append(f"{entity}: sensitivity strata are missing")
            for row in analysis_rows:
                try:
                    value = float(row.get("value", ""))
                except (TypeError, ValueError):
                    reasons.append(f"{entity}: sensitivity value is not numeric")
                    continue
                if not np.isfinite(value):
                    reasons.append(f"{entity}: sensitivity value is not finite")
            contract_field = str(spec.get("contract_id_field", "")).strip()
            if allowed_units and contract_field:
                submitted = {
                    str(row.get(contract_field, "")).strip()
                    for row in analysis_rows if str(row.get(contract_field, "")).strip()
                }
                unknown = sorted(submitted - allowed_units)
                if unknown:
                    reasons.append(f"{entity}: omitted-unit identifiers outside private sample map: {unknown[:5]}")
            pair_counts[entity] = len(units)
            continue

        if design_type == "structured_family_summary":
            # Ranked enrichment and other deterministic family summaries are
            # not patient-level hypothesis tests.  Their process evidence is
            # the complete structured family plus the originating feature and
            # stratum identifiers; no synthetic patient vector is permitted.
            # In response-ranking families the tested candidate is already
            # the feature key (entity_id).  The real pre-experiment tables use
            # candidate x patient/cohort rows and do not duplicate that key in
            # feature_id.  Accept either representation while retaining the
            # complete-family, stratum and row-level design checks.
            features = {
                str(row.get("feature_id", "")).strip()
                or str(row.get("entity_id", "")).strip()
                for row in analysis_rows
                if str(row.get("feature_id", "")).strip()
                or str(row.get("entity_id", "")).strip()
            }
            strata = {
                str(row.get("stratum_id", "")).strip()
                for row in analysis_rows if str(row.get("stratum_id", "")).strip()
            }
            units = {
                str(row.get("unit_id", "")).strip()
                for row in analysis_rows if str(row.get("unit_id", "")).strip()
            }
            blocks = {
                str(row.get("block_id", "")).strip()
                for row in analysis_rows if str(row.get("block_id", "")).strip()
            }
            if len(analysis_rows) < int(spec.get("minimum_summary_rows", 1)):
                reasons.append(f"{entity}: structured family summary has too few rows")
            if int(spec.get("minimum_feature_levels", 0)) and len(features) < int(spec["minimum_feature_levels"]):
                reasons.append(f"{entity}: structured family summary lacks feature identifiers")
            if int(spec.get("minimum_stratum_levels", 0)) and len(strata) < int(spec["minimum_stratum_levels"]):
                reasons.append(f"{entity}: structured family summary lacks stratum identifiers")
            required_strata = set(map(str, spec.get("required_strata", [])))
            if required_strata and not required_strata.issubset(strata):
                reasons.append(f"{entity}: structured family summary lacks required background strata")
            if int(spec.get("minimum_unit_levels", 0)) and len(units) < int(spec["minimum_unit_levels"]):
                reasons.append(f"{entity}: structured family summary has too few independent units")
            if int(spec.get("minimum_block_levels", 0)) and len(blocks) < int(spec["minimum_block_levels"]):
                reasons.append(f"{entity}: structured family summary has too few blocking levels")
            properties = set(map(str, spec.get("required_design_properties", [])))
            if "patient_level_scores" in properties and len(units) < int(spec.get("minimum_unit_levels", min_pairs)):
                reasons.append(f"{entity}: patient-level response scores are incomplete")
            if properties.intersection({"all_legal_boundaries", "all_legal_exclusions"}):
                minimum_scenarios = int(spec.get("minimum_stratum_levels", 2))
                if len(strata) < minimum_scenarios:
                    reasons.append(f"{entity}: legal boundary/exclusion scenarios are incomplete")
            if properties.intersection({"LOPO_sensitivity", "regularization_sensitivity"}):
                minimum_sensitivity = int(spec.get("minimum_sensitivity_strata", 2))
                if len(strata) < minimum_sensitivity:
                    reasons.append(f"{entity}: sensitivity strata are incomplete")
            pair_counts[entity] = len(analysis_rows)
            continue

        if design_type == "single_replicate_timecourse":
            # D contains one observation for each cell-line x stimulus x time
            # combination.  It supports descriptive response trajectories,
            # not a fabricated replicate-level significance test.
            required_stimuli = set(map(str, spec.get("required_stimuli", [])))
            trajectory_rows = [
                row for row in analysis_rows
                if not required_stimuli
                or str(row.get("group", "")).split("|", 1)[0] in required_stimuli
            ]
            raw_times = {
                str(row.get("time", "")).strip()
                for row in trajectory_rows if str(row.get("time", "")).strip()
            }
            def canonical_time(value: str) -> str:
                text = value.strip().lower().replace("hours", "h").replace("hour", "h")
                if "-0h" in text:
                    text = text.split("-0h", 1)[0]
                return text[:-1] if text.endswith("h") else text
            times = {canonical_time(value) for value in raw_times}
            if raw_times and all("-0h" in value.lower() for value in raw_times):
                # A baseline-difference trajectory has an implicit zero at 0h.
                times.add("0")
            # Legal exporters may place the independent cell-line identifier
            # in unit_id (and reserve block_id for genetic background) or in
            # block_id.  Select the field that actually matches the private
            # cell-line map instead of hard-coding one serialization.
            unit_matches = sum(
                str(row.get("unit_id", "")).strip() in allowed_units
                for row in trajectory_rows
            ) if allowed_units else 0
            block_matches = sum(
                str(row.get("block_id", "")).strip() in allowed_units
                for row in trajectory_rows
            ) if allowed_units else 0
            cell_line_field = "unit_id" if unit_matches > block_matches else "block_id"

            def cell_line(row: dict) -> str:
                return str(row.get(cell_line_field, "")).strip()

            blocks = {
                cell_line(row) for row in trajectory_rows if cell_line(row)
            }
            unique_keys = {
                (cell_line(row), str(row.get("group", "")), str(row.get("time", "")))
                for row in trajectory_rows
            }
            if len(times) < int(spec.get("minimum_time_levels", 2)):
                reasons.append(f"{entity}: timecourse has too few time levels")
            if len(blocks) < int(spec.get("minimum_block_levels", 1)):
                reasons.append(f"{entity}: timecourse has too few cell-line blocks")
            if len(unique_keys) != len(trajectory_rows):
                reasons.append(f"{entity}: duplicate cell-line x stimulus x time observations")
            if allowed_units:
                unknown_blocks = sorted(blocks - allowed_units)
                if unknown_blocks:
                    reasons.append(f"{entity}: cell-line blocks outside private sample map: {unknown_blocks[:5]}")
            minimum_observations = int(spec.get("minimum_observations_per_entity", 0))
            if minimum_observations and len(unique_keys) < minimum_observations:
                reasons.append(f"{entity}: incomplete cell-line x time trajectory")
            expected_times = {str(value) for value in spec.get("expected_time_values", [])}
            if expected_times and times != expected_times:
                reasons.append(f"{entity}: time grid does not match the task design")
            observed_stimuli = {
                str(row.get("group", "")).split("|", 1)[0]
                for row in trajectory_rows if str(row.get("group", "")).strip()
            }
            if required_stimuli and not required_stimuli.issubset(observed_stimuli):
                reasons.append(f"{entity}: timecourse lacks required stimuli")
            pair_counts[entity] = len(unique_keys)
            continue

        if entity_rows and not rows:
            pair_counts[entity] = 0
            continue
        groups = {str(row.get("group")) for row in analysis_rows}
        difference_encoded = paired and len(groups) == 1 and all(
            is_difference_group(group, spec.get("case_label", "case"),
                                spec.get("reference_label", "reference"))
            for group in groups
        )
        # A paired analysis may be submitted in either of two legitimate
        # encodings:
        #   1. one difference row per patient (unit_id == pair_id), or
        #   2. two long-form sample rows per patient (unit_id is the sample,
        #      pair_id is the patient and group is L/NL).
        # The private map describes independent patient units.  Treating a
        # long-form sample ID as a patient ID falsely rejects the second form.
        long_form_paired = (
            paired
            and bool(unit_contract.get("pair_id_equals_unit_id"))
            and not difference_encoded
            and any(
                str(row.get("pair_id", "")).strip()
                and str(row.get("pair_id", "")).strip() != str(row.get("unit_id", "")).strip()
                for row in analysis_rows
            )
        )
        if long_form_paired:
            observed_units = {
                str(row.get("pair_id", "")).strip() for row in analysis_rows
                if str(row.get("pair_id", "")).strip()
            }
        else:
            observed_units = {str(row.get("unit_id", "")).strip() for row in analysis_rows}
        if allowed_units:
            unknown_units = sorted(observed_units - allowed_units)
            if unknown_units:
                reasons.append(f"{entity}: units outside private sample map: {unknown_units[:5]}")
        for row in analysis_rows:
            group = str(row.get("group", ""))
            unit = str(row.get("unit_id", "")).strip()
            pair = str(row.get("pair_id", "")).strip()
            mapped_unit = pair if long_form_paired else unit
            if group and group in group_membership and mapped_unit not in group_membership[group]:
                reasons.append(f"{entity}: unit {mapped_unit} is not mapped to group {group}")
            if paired and unit_contract.get("pair_id_equals_unit_id") and not long_form_paired:
                if pair != unit:
                    reasons.append(f"{entity}: pair_id does not match private unit mapping for {unit}")
            if long_form_paired and (not unit or not pair):
                reasons.append(f"{entity}: long-form paired rows require both unit_id and pair_id")
        if design_type != "relationship" and not expected_groups.issubset(groups) and not difference_encoded:
            reasons.append(f"{entity}: missing expected groups")
        if not paired and design_type != "relationship":
            minimum_units = int(spec.get("minimum_units_per_group", 0) or 0)
            if minimum_units:
                counts = {
                    group: len({
                        str(row.get("unit_id", "")).strip()
                        for row in analysis_rows
                        if str(row.get("group", "")) == group
                        and str(row.get("unit_id", "")).strip()
                    })
                    for group in expected_groups
                }
                if any(count < minimum_units for count in counts.values()):
                    reasons.append(
                        f"{entity}: independent units {counts} do not meet "
                        f"minimum_units_per_group={minimum_units}"
                    )
        if design_type == "relationship":
            roles_by_unit: dict[str, set[str]] = {}
            for row in analysis_rows:
                roles_by_unit.setdefault(str(row.get("unit_id", "")), set()).add(str(row.get("value_role", "")))
            # A valid within-block permutation needs predictor, outcome and a
            # verified block.  A covariate row is required only by the partial
            # correlation fingerprint and is enforced inside that method's
            # recomputation.  Requiring it here rejected a fully valid block
            # analysis merely because it did not duplicate disease as a
            # numeric covariate.
            complete_units = sum({"predictor", "outcome"}.issubset(roles) for roles in roles_by_unit.values())
            pair_counts[entity] = complete_units
            if complete_units < min_pairs:
                reasons.append(f"{entity}: only {complete_units} complete relationship units")
            if "disease_block_control" in set(map(str, spec.get("required_design_properties", []))):
                for row in analysis_rows:
                    unit = str(row.get("unit_id", "")).strip()
                    block = str(row.get("block_id", "")).strip()
                    expected_blocks = unit_groups.get(unit, set())
                    if not expected_blocks or block not in expected_blocks:
                        reasons.append(f"{entity}: disease block for {unit} does not match private disease mapping")
        if paired:
            by_pair = {}
            for row in analysis_rows:
                pair = str(row.get("pair_id", row.get("unit_id", "")))
                by_pair.setdefault(pair, set()).add(str(row.get("group")))
            complete = (len(by_pair) if difference_encoded
                        else sum(expected_groups.issubset(value) for value in by_pair.values()))
            pair_counts[entity] = complete
            if complete < min_pairs:
                reasons.append(f"{entity}: only {complete} complete pairs")
        if "block_id" in requirements and any(not str(row.get("block_id", "")).strip() for row in analysis_rows):
            reasons.append(f"{entity}: missing block_id")
        if "time" in requirements:
            times = {str(row.get("time", "")).strip() for row in analysis_rows if str(row.get("time", "")).strip()}
            if len(times) < 2:
                reasons.append(f"{entity}: fewer than two time values")
        if "feature_id" in requirements and any(
            not str(row.get("feature_id", "")).strip()
            and not (
                str(spec.get("component_id", "")) == "program_family"
                and str(row.get("entity_id", "")).strip()
            )
            for row in analysis_rows
        ):
            reasons.append(f"{entity}: missing feature_id")
        if "stratum_id" in requirements and any(not str(row.get("stratum_id", "")).strip() for row in analysis_rows):
            reasons.append(f"{entity}: missing stratum_id")
        if "shared_feature_exclusion" in requirements:
            # Verify the scientific property from structured member rows.  A
            # magic word such as "deoverlapped" is not evidence.  Solvers may
            # encode feature membership with predictor_member/outcome_member;
            # the two sets must both be present and disjoint.
            predictor_features = {
                str(row.get("feature_id", "")).strip().upper()
                for row in rows if str(row.get("value_role", "")) == "predictor_member"
                and str(row.get("feature_id", "")).strip()
            }
            outcome_features = {
                str(row.get("feature_id", "")).strip().upper()
                for row in rows if str(row.get("value_role", "")) == "outcome_member"
                and str(row.get("feature_id", "")).strip()
            }
            if not predictor_features or not outcome_features:
                reasons.append(f"{entity}: feature membership needed to verify shared-feature exclusion")
            elif predictor_features & outcome_features:
                reasons.append(f"{entity}: predictor and outcome feature sets overlap")
        if "value_roles" in requirements:
            roles = {str(row.get("value_role", "")) for row in analysis_rows}
            if not {"predictor", "outcome", "covariate"}.issubset(roles):
                reasons.append(f"{entity}: incomplete value roles")
        if "non_circular" in requirements:
            # A non-circular sensitivity must be an independently encoded
            # comparison, not merely two arbitrary stratum labels.
            strata = {
                str(row.get("stratum_id", "")).strip()
                for row in analysis_rows if str(row.get("stratum_id", "")).strip()
            }
            units_by_stratum: dict[str, set[str]] = {}
            blocks_by_stratum: dict[str, set[str]] = {}
            for row in analysis_rows:
                stratum = str(row.get("stratum_id", "")).strip()
                if not stratum:
                    continue
                units_by_stratum.setdefault(stratum, set()).add(str(row.get("unit_id", "")))
                block = str(row.get("block_id", "")).strip()
                if block:
                    blocks_by_stratum.setdefault(stratum, set()).add(block)
            if len(strata) < 2 or any(len(units_by_stratum.get(value, set())) < min_pairs for value in strata):
                reasons.append(f"{entity}: non-circular sensitivity requires two adequately supported strata")
            elif blocks_by_stratum and not set.intersection(*[blocks_by_stratum.get(value, set()) for value in strata]):
                reasons.append(f"{entity}: sensitivity strata lack a shared blocking basis")
    if duplicates:
        for entity in sorted(duplicate_entities):
            reasons.append(f"{entity}: duplicate entity-unit-group observations")
    reasons = list(dict.fromkeys(reasons))
    invalid_entities = {
        entity for entity in entities
        if any(reason.startswith(f"{entity}:") for reason in reasons)
    }
    global_reasons = [
        reason for reason in reasons
        if not any(reason.startswith(f"{entity}:") for entity in entities)
    ]
    return not reasons, {"paired": paired, "design_type": design_type, "requirements": sorted(requirements),
                         "private_unit_contract_applied": bool(allowed_units),
                         "pair_counts": pair_counts, "duplicates": duplicates, "reasons": reasons,
                         "invalid_entities": sorted(invalid_entities),
                         "global_reasons": global_reasons}


def _validate_compact_rank_audit(item: dict, spec: dict) -> tuple[bool, dict]:
    contract = spec.get("rank_audit_contract", {})
    if not contract:
        return True, {"required": False}
    rows = item.get("rank_audit", [])
    manifest = item.get("rank_manifest", {})
    submitted_hash = {
        str(row.get("feature_id", ""))
        for row in rows
        if "hash_sample" in str(row.get("audit_role", "")).split("|")
    }
    expected_hash = set(map(str, contract.get("hash_sample_features", [])))
    overlap = len(submitted_hash & expected_hash)
    minimum_overlap = int(contract.get("minimum_hash_sample_overlap", 48))
    try:
        feature_count = int(manifest.get("rank_feature_count", 0))
    except (TypeError, ValueError):
        feature_count = 0
    reasons = []
    if not rows:
        reasons.append("compact rank audit is missing")
    if len(rows) > int(contract.get("audit_rows_maximum", 128)):
        reasons.append("compact rank audit exceeds the private/public maximum")
    if feature_count < int(contract.get("minimum_full_rank_features", 10000)):
        reasons.append("declared full ranking is too small")
    if overlap < minimum_overlap:
        reasons.append("deterministic gene-universe audit has insufficient overlap")
    return not reasons, {
        "required": True,
        "audit_rows": len(rows),
        "declared_rank_feature_count": feature_count,
        "hash_sample_overlap": overlap,
        "minimum_hash_sample_overlap": minimum_overlap,
        "reasons": reasons,
    }


def score_process_atom(atom: AtomDefinition, submission: dict, reference: dict) -> AtomScore:
    components = reference.get("components")
    if not components:
        return AtomScore(atom.atom_id, atom.module, atom.kind, atom.points, 0.0, "unavailable", failed=["private process reference is not configured"])
    submitted_components = {str(item.get("component_id")): item for item in submission.get("process", []) if str(item.get("atom_id")) == atom.atom_id}
    total = 0.0; passed: list[str] = []; failed: list[str] = []; diagnostics: dict[str, object] = {}
    method_states = []
    component_weight_total = sum(float(spec.get("points", 1.0)) for spec in components) or 1.0
    for spec in components:
        component_id = str(spec["component_id"])
        points = atom.points * float(spec.get("points", 1.0)) / component_weight_total
        item = submitted_components.get(component_id)
        if item is None:
            failed.append(f"{component_id}: missing process component")
            continue
        reported = item.get("reported", [])
        observations = _canonicalise_observation_units(
            item.get("observations", []), reference.get("unit_contract")
        )
        # Most data-dependent families are defined by the submitted observable
        # universe.  A small number of task resources expose a fixed public
        # universe (for example the 43 response candidates); those components
        # explicitly require that universe so a solver cannot score by testing
        # only the eventual winners.
        entities = sorted({str(row["entity_id"]) for row in reported})
        # The loader deterministically selects the audit subset before looking
        # at process values.  Deriving this set from the rows that happened to
        # survive would make missing audit rows invisible and turn the
        # completeness check into a tautology.
        method_entities = sorted({str(value) for value in item.get("audit_entity_ids", [])})
        if not method_entities:
            method_entities = sorted({str(row["entity_id"]) for row in observations})
        if not observations or not reported:
            failed.append(f"{component_id}: missing process observations or reported family")
            method_states.append("insufficient_process_data")
            diagnostics[component_id] = {
                "eligible_for_results": False,
                "record_ids": [],
                "method_distances": {}, "method_status": "insufficient_process_data", "best_method": "",
                "q_distances": {}, "q_status": "insufficient_process_data", "best_correction": "",
                "design": {"reasons": ["missing observations or reported family"]},
                "reported_family": {"missing_entities": entities},
            }
            continue
        design_fraction = float(spec.get("design_fraction", 0.30)); method_fraction = float(spec.get("method_fraction", 0.40)); fdr_fraction = 1.0 - design_fraction - method_fraction
        reported_valid, reported_diagnostics = _validate_reported_family(
            reported,
            entities,
            require_inference=(method_fraction > 1e-12 or fdr_fraction > 1e-12),
        )
        method_reported_valid, method_reported_diagnostics = _validate_reported_family(
            reported,
            entities,
            require_inference=(method_fraction > 1e-12),
            required_numeric_fields=("effect", "statistic", "p_value")
            if method_fraction > 1e-12 else ("effect",),
        )
        observed_entities = {str(row["entity_id"]) for row in observations}
        nonobservable_entities = set(reported_diagnostics["nonobservable_entities"])
        expected_nonobservable = {
            str(value) for value in spec.get("nonobservable_entities", [])
        }
        completeness_properties = set(map(str, spec.get("required_design_properties", [])))
        complete_family_observability = bool(completeness_properties.intersection({
            "complete_library", "complete_regulon_family", "declared_family_multiplicity",
        }))
        variability = str(spec.get("answer_variability", "LOW")).upper()
        exact_observability = bool(spec.get("fixed_public_universe", False)) or variability == "LOW"
        if "nonobservable_entities" in spec and (exact_observability or not complete_family_observability):
            if nonobservable_entities != expected_nonobservable:
                reported_valid = False
                reported_diagnostics["expected_nonobservable_entities"] = sorted(expected_nonobservable)
                reported_diagnostics["unexpected_nonobservable_entities"] = sorted(
                    nonobservable_entities - expected_nonobservable
                )
                reported_diagnostics["missing_nonobservable_entities"] = sorted(
                    expected_nonobservable - nonobservable_entities
                )
        elif complete_family_observability:
            # In a variable LIANA/regulon/library universe, exact NA identities
            # are themselves unstable.  Preserve the reference-observable core
            # instead of requiring an identical NA list, while still blocking
            # a solver from marking the whole family unobservable to evade the
            # method and multiplicity checks.
            expected_signatures = {
                _family_signature(component_id, value)
                for value in spec.get("family_entities", []) if str(value).strip()
            }
            expected_na_signatures = {
                _family_signature(component_id, value) for value in expected_nonobservable
            }
            submitted_observable_signatures = {
                _family_signature(component_id, value)
                for value in entities if value not in nonobservable_entities
            }
            expected_observable = expected_signatures - expected_na_signatures
            observable_core_coverage = (
                len(expected_observable & submitted_observable_signatures) / len(expected_observable)
                if expected_observable else 1.0
            )
            compact_variable_family = bool(
                str(spec.get("family_validation_mode", "")) == "compact_resource_family"
                and not bool(spec.get("fixed_public_universe", False))
            )
            minimum_observable_coverage = float(spec.get(
                "minimum_reference_observable_coverage",
                0.75 if variability == "HIGH" else 0.85,
            ))
            reported_diagnostics["reference_observable_core_coverage"] = observable_core_coverage
            reported_diagnostics["reference_observable_core_is_informational"] = compact_variable_family
            reported_diagnostics["minimum_reference_observable_coverage"] = (
                0.0 if compact_variable_family else minimum_observable_coverage
            )
            # A compact HIGH/MODERATE family is validated by its public
            # resource manifest and deterministic audit subset.  Its hidden
            # preexperiment members are examples, not an exhaustive answer
            # key.  Requiring 75/85% overlap here contradicted that contract
            # and rejected valid library/annotation versions.  Still reject
            # the vacuous "everything is unobservable" escape hatch.
            if compact_variable_family and not submitted_observable_signatures:
                reported_valid = False
                reported_diagnostics.setdefault("invalid_fields", []).append(
                    "compact family has no observable audit member"
                )
            elif (
                not compact_variable_family
                and observable_core_coverage + 1e-12 < minimum_observable_coverage
            ):
                reported_valid = False
                reported_diagnostics.setdefault("invalid_fields", []).append(
                    "observable family core is too incomplete"
                )
        method_observations_complete = bool(method_entities) and set(method_entities).issubset(
            observed_entities | nonobservable_entities
        )
        unit_design_valid, design_diagnostics = _validate_design(
            observations,
            method_entities,
            spec,
            nonobservable_entities,
            reference.get("unit_contract"),
        )
        # Keep direct dependencies separate.  A valid numerical method
        # fingerprint requires the correct independent units/design, whereas
        # family completeness and a compact rank audit are separate process
        # properties.  Collapsing all three into one flag either lets a wrong
        # unit analysis earn method points or makes an unrelated family error
        # erase otherwise valid method evidence.
        rank_valid = True
        if str(spec.get("design_type", "")) == "gene_set_enrichment":
            rank_valid, rank_diagnostics = _validate_compact_rank_audit(item, spec)
            rank_required = bool(spec.get("require_compact_rank_audit", False))
            rank_diagnostics["required"] = rank_required
            design_diagnostics["rank_audit"] = rank_diagnostics
            if not rank_required:
                rank_valid = True
            elif not rank_valid:
                design_diagnostics.setdefault("reasons", []).extend(rank_diagnostics["reasons"])
        required_family = {str(value) for value in spec.get("required_family_entities", [])}
        fixed_family_valid = True
        if required_family:
            submitted_family = set(entities)
            missing_required = sorted(required_family - submitted_family)
            unexpected = sorted(submitted_family - required_family)
            design_diagnostics["required_family_size"] = len(required_family)
            design_diagnostics["submitted_family_size"] = len(submitted_family)
            design_diagnostics["missing_required_entities"] = missing_required
            design_diagnostics["unexpected_entities"] = unexpected
            if missing_required or unexpected:
                fixed_family_valid = False
                design_diagnostics.setdefault("reasons", []).append(
                    "submitted family does not equal the fixed public candidate universe"
                )
        family_valid, family_diagnostics = _validate_family_signatures(
            component_id, spec, entities
        )
        design_diagnostics["family_membership"] = family_diagnostics
        if not family_valid:
            design_diagnostics.setdefault("reasons", []).append(
                "submitted family does not satisfy the complete-family equivalence contract"
            )
        complete_design_valid = bool(
            unit_design_valid and rank_valid and fixed_family_valid and family_valid
        )
        invalid_unit_entities = set(map(str, design_diagnostics.get("invalid_entities", [])))
        unit_design_global_valid = not design_diagnostics.get("global_reasons", [])
        unit_valid_entities = set(method_entities) - invalid_unit_entities
        unit_design_match_fraction = (
            len(unit_valid_entities) / len(method_entities) if method_entities else 0.0
        )
        design_diagnostics["unit_design_valid"] = bool(unit_design_valid)
        design_diagnostics["unit_design_global_valid"] = bool(unit_design_global_valid)
        design_diagnostics["unit_design_match_fraction"] = unit_design_match_fraction
        design_diagnostics["rank_valid"] = bool(rank_valid)
        design_diagnostics["fixed_family_valid"] = bool(fixed_family_valid)
        design_diagnostics["family_valid"] = bool(family_valid)
        design_diagnostics["complete_design_valid"] = complete_design_valid
        if (
            method_observations_complete and observations and reported_valid
            and unit_design_global_valid and rank_valid and fixed_family_valid and family_valid
            and unit_design_match_fraction > 0
        ):
            total += points * design_fraction * unit_design_match_fraction
            passed.append(
                f"{component_id}: design/family evidence present for "
                f"{len(unit_valid_entities)}/{len(method_entities)} audited entities"
            )
        else:
            failed.append(f"{component_id}: incomplete or invalid design")

        methods, acceptable_methods, rejected_methods = _method_policy(spec)
        declared_method_text = {
            str(row.get("method", "")).strip() for row in reported
            if bool(row.get("observable", True)) and str(row.get("method", "")).strip()
        }
        known_method_codes = set(methods) | acceptable_methods | rejected_methods
        declared_methods: set[str] = set()
        for declaration in declared_method_text:
            declared_methods.update(_normalise_method_declaration(declaration, known_method_codes))
        # If the submitter names one or more recognised procedures, recompute
        # those procedures rather than every allowed alternative.  This both
        # verifies the declaration and avoids exponential work for an unused
        # exact test (for example 2^26 sign flips when paired t was reported).
        declared_supported = set(methods).intersection(declared_methods)
        submitted_groups = {
            str(row.get("group", "")) for row in observations
            if bool(row.get("observable", True))
        }
        raw_paired_arms_available = bool(
            spec.get("paired", False)
            and str(spec.get("case_label", "case")) in submitted_groups
            and str(spec.get("reference_label", "reference")) in submitted_groups
        )
        if declared_supported:
            # A solver declaration may select which expensive acceptable
            # fingerprint is worth recomputing, but it must never suppress a
            # scientifically rejected comparator.  Otherwise simply writing
            # "paired t" hides the cheap unpaired-t fingerprint and can turn a
            # wrong analysis into an apparent acceptable match.
            methods_to_compute = [
                method for method in methods
                if method in declared_supported or method in rejected_methods
            ]
        else:
            methods_to_compute = list(methods)
        # A table of already-computed within-patient differences identifies a
        # one-sample paired analysis but does not contain the two raw arms
        # needed to reconstruct the competing "ignore pairing" analysis.  Do
        # not manufacture a zero-valued reference arm and call that the
        # rejected unpaired method; it is a different test and caused valid
        # difference-vector submissions to be marked ambiguous.
        if not raw_paired_arms_available:
            methods_to_compute = [
                method for method in methods_to_compute
                if method != "unpaired_t_on_paired_values"
            ]
        observations_by_entity: dict[str, list[dict]] = {}
        for row in observations:
            observations_by_entity.setdefault(str(row.get("entity_id", "")), []).append(row)
        method_outputs: dict[str, dict[str, dict[str, float]]] = {}
        method_distance_profiles: dict[str, dict[str, float]] = {}
        if method_fraction > 1e-12:
            for method in methods_to_compute:
                output = {}
                for entity_id in method_entities:
                    rows = observations_by_entity.get(entity_id, [])
                    if entity_id in set(reported_diagnostics["nonobservable_entities"]):
                        output[entity_id] = {"effect": np.nan, "statistic": np.nan, "p_value": np.nan}
                        continue
                    try:
                        output[entity_id] = compute_method(rows, spec, method)
                    except Exception:
                        output[entity_id] = {"effect": np.nan, "statistic": np.nan, "p_value": np.nan}
                method_outputs[method] = output
            method_distance_profiles = {
                name: _numeric_distance_profile(reported, output)
                for name, output in method_outputs.items()
            }
            method_distances = {
                name: (float(np.max(list(profile.values()))) if profile else float("inf"))
                for name, profile in method_distance_profiles.items()
            }
            method_status, best_method, best_distance, second_distance = _infer(
                method_distances,
                acceptable_methods,
                float(spec.get("method_indistinguishable_tolerance", 1e-8)),
                float(spec.get("method_maximum_match_distance", 0.35)),
            )
        else:
            method_distances = {}
            method_distance_profiles = {}
            method_status, best_method = "not_applicable", ""
            best_distance = second_distance = float("inf")
        near_best_methods = {
            name for name, distance in method_distances.items()
            if np.isfinite(distance)
            and distance - best_distance <= float(spec.get("method_ambiguity_margin", 0.15))
        }
        if method_fraction <= 1e-12:
            method_status = "not_applicable"
        elif not method_reported_valid:
            method_status = "insufficient_process_data"
        elif declared_methods & rejected_methods:
            method_status = f"declared_rejected_method:{','.join(sorted(declared_methods & rejected_methods))}"
        elif not near_best_methods.intersection(acceptable_methods):
            method_status = "declared_acceptable_but_numeric_fingerprint_inconsistent"
        elif declared_methods and not declared_methods.issubset(acceptable_methods):
            method_status = f"unrecognized_or_inconsistent_method_declaration:{','.join(sorted(declared_methods))}"
        elif near_best_methods.intersection(rejected_methods):
            # If an explicitly rejected procedure is numerically
            # indistinguishable from an acceptable one on this audit subset,
            # the method is not identifiable.  A free-text declaration cannot
            # turn that ambiguity into positive method evidence.
            method_status = "ambiguous_between_acceptable_and_rejected_method"
        elif near_best_methods.intersection(acceptable_methods):
            # Free-form or absent declarations do not veto a clear,
            # recomputable acceptable fingerprint.
            method_status = "confirmed_acceptable_method"
        method_match_threshold = float(spec.get("method_maximum_match_distance", 0.35))
        acceptable_profile_names = set(method_distance_profiles).intersection(acceptable_methods)
        best_acceptable_method = min(
            acceptable_profile_names,
            key=lambda name: method_distances.get(name, float("inf")),
            default="",
        )
        method_profile = method_distance_profiles.get(best_acceptable_method, {})
        # Recomputed fingerprints are deterministic conditional on the
        # submitted units.  A rejected method is indistinguishable only when
        # it is tied with the best acceptable method to numerical precision;
        # a broad distance margin wrongly rejects exact acceptable matches
        # merely because the wrong test happens to give a similar p-value.
        method_indistinguishable_tolerance = float(
            spec.get("method_indistinguishable_tolerance", 1e-8)
        )
        rejected_profile_names = set(method_distance_profiles).intersection(rejected_methods)
        method_passing_entities = {
            entity for entity, distance in method_profile.items()
            if np.isfinite(distance)
            and distance <= method_match_threshold
            and not any(
                np.isfinite(method_distance_profiles[name].get(entity, float("inf")))
                and method_distance_profiles[name].get(entity, float("inf"))
                    <= distance + method_indistinguishable_tolerance
                for name in rejected_profile_names
            )
        }
        method_passing_entities &= unit_valid_entities
        method_match_fraction = (
            len(method_passing_entities) / len(method_profile) if method_profile else 0.0
        )
        if (
            method_fraction > 1e-12
            and method_match_fraction > 0
            and method_status not in {
                "confirmed_acceptable_method", "ambiguous_with_acceptable_method",
            }
            and not (declared_methods & rejected_methods)
        ):
            method_status = "partially_compatible_acceptable_method"
        if (
            method_fraction > 1e-12
            and method_match_fraction < 1.0 - 1e-12
            and method_status in {"confirmed_acceptable_method", "ambiguous_with_acceptable_method"}
        ):
            method_status = (
                "partially_compatible_acceptable_method"
                if method_match_fraction > 0
                else "ambiguous_between_acceptable_and_rejected_method"
            )
        elif (
            method_fraction > 1e-12
            and method_match_fraction >= 1.0 - 1e-12
            and not (declared_methods & rejected_methods)
            and (not declared_methods or declared_methods.issubset(acceptable_methods))
        ):
            method_status = "confirmed_acceptable_method"
        # Score recomputable method evidence at the entity level.  Requiring
        # every entity in a component to have a complete observation block
        # made one local omission erase method credit for all other entities.
        # Global unit-contract failures and malformed reported families still
        # block the component; locally incomplete entities have already been
        # removed from ``method_passing_entities``.
        method_input_design_valid = bool(
            observations and method_reported_valid
            and unit_design_global_valid and bool(unit_valid_entities)
        )
        if method_input_design_valid and method_status in {"confirmed_acceptable_method", "ambiguous_with_acceptable_method"}:
            total += points * method_fraction * method_match_fraction
            if method_match_fraction >= 1.0 - 1e-12:
                passed.append(f"{component_id}: acceptable method fingerprint ({best_method})")
            elif method_match_fraction > 0:
                passed.append(
                    f"{component_id}: acceptable method fingerprint for "
                    f"{len(method_passing_entities)}/{len(method_profile)} audited entities"
                )
        elif method_input_design_valid and method_status == "partially_compatible_acceptable_method":
            total += points * method_fraction * method_match_fraction
            passed.append(
                f"{component_id}: locally acceptable method fingerprint for "
                f"{len(method_passing_entities)}/{len(method_profile)} audited entities"
            )
        elif method_input_design_valid and method_status == "ambiguous_between_acceptable_and_rejected_method":
            # The submitted numbers do not identify which of two procedures
            # was used.  This is evidence for neither a full pass nor a full
            # failure: award bounded process credit, but keep downstream
            # scientific results ineligible until the method is identifiable.
            total += points * method_fraction * 0.5
            passed.append(f"{component_id}: method fingerprint is only partially identifiable")
        elif method_fraction > 1e-12:
            if not method_input_design_valid:
                failed.append(f"{component_id}: method fingerprint lacks a valid independent-unit design")
            failed.append(f"{component_id}: {method_status}")

        reported_by_entity = {str(row["entity_id"]): row for row in reported}
        # BH is meaningful only for the multiplicity family that was actually
        # prespecified.  Correct arithmetic on a cherry-picked or otherwise
        # invalid family is not "full-family BH" evidence.  This gate is kept
        # separate from unrelated unit/design checks so a valid correction is
        # not denied merely because another process property failed.
        multiplicity_family_valid = bool(reported_valid and family_valid)
        if required_family:
            multiplicity_family_valid = bool(
                multiplicity_family_valid
                and not design_diagnostics.get("missing_required_entities")
                and not design_diagnostics.get("unexpected_entities")
            )
        if fdr_fraction <= 1e-12:
            q_distances = {}
            q_status, best_q = "not_applicable", ""
            q_best_distance = q_second_distance = float("inf")
        elif multiplicity_family_valid:
            # Multiple-testing inference must be conditional on the model's own
            # raw P values. Otherwise a wrong primary test with correct BH would
            # be incorrectly diagnosed as both a primary-test and BH error.
            reported_p_values = np.asarray([
                float(reported_by_entity[entity]["p_value"])
                if bool(reported_by_entity[entity].get("observable", True))
                else float(spec.get("nonobservable_p_value", np.nan))
                for entity in entities
            ], float)
            corrections = correction_candidates(reported_p_values, np.ones(len(entities), dtype=bool))
            # With a complete submitted family, "submitted subset" is the full
            # family and is not an alternative error mechanism.
            corrections.pop("bh_submitted_subset", None)
            q_distance_profiles = {
                name: _q_distance_profile(reported, entities, values)
                for name, values in corrections.items()
            }
            q_distances = {
                name: (float(np.max(list(profile.values()))) if profile else float("inf"))
                for name, profile in q_distance_profiles.items()
            }
            q_status, best_q, q_best_distance, q_second_distance = _infer(
                q_distances,
                {"bh_full"},
                float(spec.get("q_indistinguishable_tolerance", 1e-10)),
                float(spec.get("q_maximum_match_distance", 0.20)),
            )
        else:
            q_distances = {}
            q_distance_profiles = {}
            q_status, best_q = "invalid_multiplicity_family", ""
            q_best_distance = q_second_distance = float("inf")
        if fdr_fraction <= 1e-12:
            q_distance_profiles = {}
        q_match_threshold = float(spec.get("q_maximum_match_distance", 0.20))
        bh_profile = q_distance_profiles.get("bh_full", {})
        q_indistinguishable_tolerance = float(
            spec.get("q_indistinguishable_tolerance", 1e-10)
        )
        q_near_best = {
            name for name, distance in q_distances.items()
            if np.isfinite(distance)
            and distance - q_best_distance <= q_indistinguishable_tolerance
        }
        if (
            q_status in {"confirmed_acceptable_method", "ambiguous_with_acceptable_method"}
            and "bh_full" in q_near_best
            and (q_near_best - {"bh_full"})
        ):
            # Numerically identical corrections establish that the submitted
            # q values are BH-compatible, but not that BH itself was the
            # procedure used.  Preserve result eligibility while withholding
            # a full process-method claim.
            q_status = "ambiguous_between_bh_and_other_correction"
        q_passing_entities = {
            entity for entity, distance in bh_profile.items()
            if np.isfinite(distance) and distance <= q_match_threshold
        }
        q_match_fraction = len(q_passing_entities) / len(bh_profile) if bh_profile else 0.0
        if (
            fdr_fraction > 1e-12 and multiplicity_family_valid
            and q_match_fraction > 0
            and q_status not in {
                "confirmed_acceptable_method", "ambiguous_with_acceptable_method",
                "ambiguous_between_bh_and_other_correction",
            }
        ):
            q_status = "partially_compatible_bh"
        if q_status in {"confirmed_acceptable_method", "ambiguous_with_acceptable_method"}:
            total += points * fdr_fraction * q_match_fraction
            if q_match_fraction >= 1.0 - 1e-12:
                passed.append(f"{component_id}: full-family BH fingerprint")
            elif q_match_fraction > 0:
                passed.append(
                    f"{component_id}: BH-compatible q values for "
                    f"{len(q_passing_entities)}/{len(bh_profile)} family members"
                )
        elif q_status == "partially_compatible_bh":
            total += points * fdr_fraction * q_match_fraction
            passed.append(
                f"{component_id}: locally BH-compatible q values for "
                f"{len(q_passing_entities)}/{len(bh_profile)} family members"
            )
        elif q_status == "ambiguous_between_bh_and_other_correction":
            total += points * fdr_fraction * q_match_fraction * 0.5
            passed.append(
                f"{component_id}: q values are BH-compatible but the correction is not identifiable"
            )
        elif fdr_fraction > 1e-12:
            failed.append(f"{component_id}: {q_status}")
        method_required = method_fraction > 1e-12
        fdr_required = fdr_fraction > 1e-12
        method_eligible = bool(method_passing_entities) if method_required else True
        fdr_eligible = bool(q_passing_entities) if fdr_required else True
        eligible_entities = set(entities)
        if method_required:
            eligible_entities &= method_passing_entities
        if fdr_required:
            eligible_entities &= q_passing_entities
        reported_record_by_entity = {
            str(row.get("entity_id", "")): str(row.get("record_id", ""))
            for row in reported if str(row.get("record_id", ""))
        }
        result_design_scope_valid = bool(
            unit_design_global_valid and rank_valid and fixed_family_valid and family_valid
        )
        eligible_entities &= unit_valid_entities
        # Eligibility is local once the multiplicity family and the global
        # design contract are valid.  ``method_observations_complete`` means
        # that *every* audited entity has a complete observation block; using
        # it here made one locally incomplete entity erase otherwise
        # recomputable records from the same component.  The per-entity
        # intersections above already retain only rows with a valid unit
        # design, an acceptable primary-test fingerprint and a compatible BH
        # value.  Global family/design failures remain non-compensatory via
        # ``reported_valid`` and ``result_design_scope_valid``.
        eligible_record_ids = sorted({
            reported_record_by_entity[entity]
            for entity in eligible_entities if entity in reported_record_by_entity
        }) if (
            reported_valid and result_design_scope_valid
            and method_eligible and fdr_eligible
        ) else []
        eligible_for_results = bool(eligible_record_ids)
        method_states.append(method_status)
        diagnostics[component_id] = {
            "eligible_for_results": eligible_for_results,
            "record_ids": list(item.get("record_ids", [])),
            "eligible_record_ids": eligible_record_ids,
            "record_entities": {
                str(row.get("record_id", "")): _evidence_semantic_text(row)
                for row in reported if str(row.get("record_id", ""))
            },
            "method_distances": method_distances,
            "method_distance_profiles": method_distance_profiles,
            "method_match_fraction": method_match_fraction,
            "method_input_design_valid": method_input_design_valid,
            "method_reported_family": method_reported_diagnostics,
            "method_passing_entities": sorted(method_passing_entities),
            "method_status": method_status,
            "best_method": best_method,
            "best_method_distance": best_distance,
            "second_method_distance": second_distance,
            "method_check_entities": method_entities,
            "acceptable_methods": sorted(acceptable_methods),
            "rejected_methods": sorted(rejected_methods),
            "declared_method_text": sorted(declared_method_text),
            "declared_methods": sorted(declared_methods),
            "near_best_methods": sorted(near_best_methods),
            "multiplicity_family_valid": multiplicity_family_valid,
            "q_distances": q_distances,
            "q_distance_profiles": q_distance_profiles,
            "q_match_fraction": q_match_fraction,
            "q_passing_entities": sorted(q_passing_entities),
            "q_status": q_status,
            "q_near_best_corrections": sorted(q_near_best),
            "best_correction": best_q,
            "best_q_distance": q_best_distance,
            "second_q_distance": q_second_distance,
            "design": design_diagnostics,
            "reported_family": reported_diagnostics,
        }
    status = "scored" if abs(total - atom.points) < 1e-9 else ("partial" if total > 0 else "failed")
    method_inference = ";".join(method_states)
    return AtomScore(atom.atom_id, atom.module, atom.kind, atom.points, min(total, atom.points), status, method_inference, passed, failed, diagnostics)

