from __future__ import annotations

import re
import math
from dataclasses import replace

from .models import AtomDefinition, AtomScore
from .results import (
    _candidate_family_identity,
    _localization_identity_is_linked,
    _result_eligibility,
    _soft_result_quality,
    _routed_to_result_atom,
    _semantic_tokens,
    _target_context_compatible,
    score_conclusion_atom,
)


def _norm(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", str(value).upper()).strip()


def _row_values(row: dict) -> list[str]:
    return [str(row.get("entity_id", "")), *map(str, row.get("semantic_aliases", []))]


def _material_identity_compatible(target: dict, row: dict) -> bool:
    """Return whether a row belongs to the material named by the target.

    Material membership is part of the claimed object identity, not a quality
    bonus.  An A response can be a well measured response while still being
    no evidence at all for a specifically C-scoped result.
    """
    prefixes = {_norm(value) for value in target.get("allowed_scope_prefixes", []) if _norm(value)}
    if not prefixes:
        return True
    observed = _norm(str(row.get("scope", "")).split("|", 1)[0])
    return observed in prefixes


def _exact_or_theme_identity(hit: dict, target: dict, row: dict) -> tuple[str, float] | None:
    entity_terms = [value for value in target.get("identity_entity_any", []) if _norm(value)]
    contrast_terms = [value for value in target.get("identity_contrast_any", []) if _norm(value)]
    if entity_terms or contrast_terms:
        entity_tokens = set().union(*(_semantic_tokens(value) for value in _row_values(row)))
        contrast_tokens = _semantic_tokens(row.get("contrast", ""))
        entity_ok = not entity_terms or any(
            _semantic_tokens(term).issubset(entity_tokens) for term in entity_terms
        )
        contrast_ok = not contrast_terms or any(
            _semantic_tokens(term).issubset(contrast_tokens) for term in contrast_terms
        )
        if entity_ok and contrast_ok:
            return f"COMPOUND:{_norm(target.get('entity_id', ''))}", 1.0

    accepted = [
        target.get("entity_id", ""),
        *target.get("accepted_entity_ids", []),
        *target.get("evidence_entity_patterns", []),
    ]
    accepted_norm = {_norm(value) for value in accepted if _norm(value)}
    observed = {_norm(value) for value in _row_values(row) if _norm(value)}
    overlap = accepted_norm & observed
    if overlap:
        return f"EXACT:{sorted(overlap)[0]}", 1.0

    if str(hit.get("mode")) != "theme_hit":
        return None
    concepts = {_norm(value) for value in hit.get("concept_any", []) if _norm(value)}
    observed_tokens = set().union(*(_semantic_tokens(value) for value in _row_values(row)))
    concept_tokens = set().union(*(_semantic_tokens(value) for value in concepts)) if concepts else set()
    matched = observed_tokens & concept_tokens
    if not matched:
        return None
    # Theme matching is deliberately coarse only after the statistical and
    # evidence gates pass.  The identity key prevents two synonymous strings
    # for the same theme from creating two hits.
    # Distinct theme hits are distinct scientific source targets (for example
    # endothelial and mural programmes, or A and B concordance), not distinct
    # spellings of the same broad theme.  Keying only by hit_id made every
    # required_distinct_hits>1 theme mathematically impossible.
    return f"THEME:{str(hit.get('hit_id'))}:{str(target.get('entity_id', ''))}", 1.0


def _match_option(hit: dict, target: dict, row: dict) -> tuple[str, float] | None:
    if bool(hit.get("accept_any_evidence_backed_candidate", False)):
        entity = _norm(row.get("entity_id", ""))
        if entity:
            return f"EVIDENCE_BACKED:{entity}", 1.0
    if str(target.get("scoring_mode")) in {"candidate_family", "conditional_localization"}:
        return _candidate_family_identity(target, row)
    return _exact_or_theme_identity(hit, target, row)


def _ordered_rows(rows: list[dict], maximum: int) -> list[dict]:
    def key(row: dict) -> tuple:
        try:
            rank = float(row.get("rank"))
        except (TypeError, ValueError):
            rank = float("inf")
        return rank, str(row.get("record_id", ""))

    return sorted(rows, key=key)[:maximum]


def _float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _explicit_candidate_nominations(submission: dict, stage: str, maximum: int) -> list[str]:
    """Return the bounded, explicitly submitted candidate shortlist.

    Full ranking tables are process evidence, not an implicit nomination of
    every row.  A structured shortlist, when present, therefore determines
    which identities may earn candidate-result points.  Oversized shortlists
    are truncated locally instead of invalidating unrelated atoms.
    """
    values: list[str] = []
    seen: set[str] = set()
    # A scientifically valid shortlist can fail semantic routing to a
    # particular conclusion atom while remaining a schema-valid record.  Use
    # both routed conclusions and validated raw records for nomination only;
    # this does not make the raw record scientific evidence.
    rows = [*submission.get("conclusions", []), *submission.get("raw_records", [])]
    visited: set[str] = set()
    for row in rows:
        record_id = str(row.get("record_id", ""))
        if record_id and record_id in visited:
            continue
        if record_id:
            visited.add(record_id)
        if str(row.get("record_type", "conclusion")) != "conclusion":
            continue
        if str(row.get("stage", "")).upper() != str(stage).upper():
            continue
        selected = row.get("selected_candidates")
        if not isinstance(selected, list):
            continue
        for value in selected:
            key = _norm(value)
            if key and key not in seen:
                values.append(key)
                seen.add(key)
            if len(values) >= maximum:
                return values
    return values


def _candidate_group_quality(
    rule: str | None,
    members: list[tuple[dict, dict, float]],
    observed: list[dict],
) -> tuple[bool, list[str]]:
    """Qualify a candidate class from submitted sensitivity evidence.

    This deliberately scores properties rather than fixed candidate names.
    Cutoffs are relative to the submitted complete candidate universe, so a
    harmless rank fluctuation cannot fail an otherwise equivalent analysis.
    """
    if not rule:
        return True, []
    rows = [item[0] for item in members]
    by_scope: dict[str, dict] = {}
    for row in rows:
        prefix = str(row.get("scope", "")).split("|", 1)[0].upper()
        if prefix in {"A", "B"}:
            by_scope[prefix] = row
    failures: list[str] = []
    if set(by_scope) != {"A", "B"}:
        return False, ["candidate class requires the same identity in both A and B"]

    universe_by_scope: dict[str, int] = {}
    for prefix in ("A", "B"):
        scoped = [
            row for row in observed
            if str(row.get("scope", "")).split("|", 1)[0].upper() == prefix
        ]
        identities = {_norm(row.get("entity_id", "")) for row in scoped if _norm(row.get("entity_id", ""))}
        # Result routing may retain only scientifically admissible candidate
        # identities.  The submitted rank and leave-one rank still expose a
        # lower bound for the complete evaluated universe and must be used;
        # counting routed rows alone would turn a 43-candidate analysis into
        # an apparent 8-candidate analysis and reject every valid rank.
        rank_extent = max(
            [value for row in scoped for value in (_float(row.get("rank")), _float(row.get("loo_rank_max")))
             if value is not None] or [0]
        )
        universe_by_scope[prefix] = max(len(identities), int(math.ceil(rank_extent)))
        if universe_by_scope[prefix] < 2:
            failures.append(f"{prefix} candidate universe is not auditable")

    metrics: dict[str, dict[str, float | bool | None]] = {}
    for prefix, row in by_scope.items():
        metrics[prefix] = {
            "rank": _float(row.get("rank")),
            "loo_min": _float(row.get("loo_rank_min")),
            "loo_max": _float(row.get("loo_rank_max")),
            "sign_agreement": _float(row.get("loo_sign_agreement")),
            "endpoint_sensitive": bool(row.get("endpoint_sign_sensitive", False)),
        }
        if str(row.get("direction", "")).lower() != "increase":
            failures.append(f"{prefix} direction is not concordantly increased")
        if any(metrics[prefix][key] is None for key in ("rank", "loo_min", "loo_max", "sign_agreement")):
            failures.append(f"{prefix} lacks rank/leave-one sensitivity evidence")
    if failures:
        return False, failures

    if rule == "stable_ab_ranked":
        for prefix in ("A", "B"):
            n = universe_by_scope[prefix]
            top_third = max(1, math.ceil(n / 3))
            top_half = max(1, math.ceil(n / 2))
            item = metrics[prefix]
            if float(item["rank"]) > top_third or float(item["loo_max"]) > top_half:
                failures.append(f"{prefix} is outside the relatively stable ranked region")
            if float(item["sign_agreement"]) < 1.0 or bool(item["endpoint_sensitive"]):
                failures.append(f"{prefix} is direction/boundary sensitive")
    elif rule == "boundary_sensitive_ab_ranked":
        sensitivity_seen = False
        for prefix in ("A", "B"):
            n = universe_by_scope[prefix]
            top_half = max(1, math.ceil(n / 2))
            spread_floor = max(4, math.ceil(n / 8))
            item = metrics[prefix]
            if float(item["rank"]) > top_half:
                failures.append(f"{prefix} is outside the priority half of the candidate universe")
            spread = float(item["loo_max"]) - float(item["loo_min"])
            sensitivity_seen = sensitivity_seen or spread >= spread_floor
            sensitivity_seen = sensitivity_seen or float(item["sign_agreement"]) < 1.0
            sensitivity_seen = sensitivity_seen or bool(item["endpoint_sensitive"])
        if not sensitivity_seen:
            failures.append("no rank variation or leave-one/boundary sensitivity was demonstrated")
    else:
        failures.append(f"unknown candidate qualification rule: {rule}")
    return not failures, failures


def score_result_hit_atom(
    atom: AtomDefinition,
    submission: dict,
    reference: dict,
    eligible_evidence_ids: set[str] | None = None,
    eligible_evidence_by_component: dict[str, set[str]] | None = None,
    eligible_evidence_entities_by_component: dict[str, dict[str, str]] | None = None,
) -> AtomScore:
    hit_atoms = reference.get("hit_atoms", [])
    targets = {str(target.get("entity_id")): target for target in reference.get("targets", [])}
    if not hit_atoms:
        return AtomScore(
            atom.atom_id, atom.module, atom.kind, atom.points, 0.0, "unavailable",
            failed=["private key-hit atoms are not configured"],
        )
    observed = [
        row for row in submission.get("results", [])
        if _routed_to_result_atom(row, atom.atom_id)
    ]
    if bool(reference.get("include_structured_conclusions", False)):
        for conclusion in submission.get("conclusions", []):
            if str(conclusion.get("stage", "")).upper() != str(atom.module).upper():
                continue
            subject_id = str(conclusion.get("subject_id", "")).strip()
            object_id = str(conclusion.get("object_id", "")).strip()
            if not subject_id and not object_id:
                continue
            observed.append({
                **conclusion,
                "record_type": "result",
                "analysis_type": "synthesis",
                "entity_id": subject_id or object_id,
                "semantic_aliases": [value for value in (subject_id, object_id) if value],
                "scope": str(conclusion.get("claim_scope", "module")),
                "contrast": "",
                "effect": None,
                "support_status": conclusion.get("support_status", conclusion.get("status")),
                "candidate_atom_ids": [atom.atom_id],
            })
    eligible_evidence_ids = eligible_evidence_ids or set()
    eligible_evidence_by_component = eligible_evidence_by_component or {}
    eligible_evidence_entities_by_component = eligible_evidence_entities_by_component or {}
    require_evidence = bool(reference.get("require_eligible_evidence", True))
    consumed: set[str] = set()
    consumed_candidate_identities: set[str] = set()
    eligible_record_ids: list[str] = []
    eligible_record_targets: dict[str, str] = {}
    eligible_record_hits: dict[str, str] = {}
    passed: list[str] = []
    failed: list[str] = []
    details: list[dict] = []
    total = 0.0

    # Specific endpoints and boundaries consume records before broad themes.
    # This is an anti-reuse priority, not a claim that the reference answer is
    # unique or exhaustive.
    priority = {"fixed_hit": 0, "boundary_hit": 1, "theme_hit": 2, "candidate_hit": 3}
    indexed_hits = list(enumerate(hit_atoms))
    indexed_hits.sort(key=lambda item: (priority.get(str(item[1].get("mode")), 9), -float(item[1].get("points", 0)), item[0]))
    detail_by_index: dict[int, dict] = {}

    for original_index, hit in indexed_hits:
        hit_id = str(hit.get("hit_id"))
        points = float(hit.get("points", 0.0))
        required = max(1, int(hit.get("required_distinct_hits", 1)))
        maximum = max(required, int(hit.get("maximum_nominations", 8)))
        explicit_nominations = (
            set(_explicit_candidate_nominations(submission, atom.module, maximum))
            if bool(hit.get("uses_stage_shortlist", False)) else set()
        )
        options = [targets[value] for value in hit.get("source_target_ids", []) if value in targets]
        candidates: dict[str, dict] = {}
        rejected: list[dict] = []
        matched_rows: list[tuple[dict, dict]] = []
        candidate_groups: dict[tuple[str, str], list[tuple[dict, dict, float]]] = {}
        preselected_record_ids: set[str] | None = None
        if str(hit.get("mode")) != "candidate_hit":
            raw_matches: list[dict] = []
            for row in observed:
                record_id = str(row.get("record_id", ""))
                if not record_id or record_id in consumed:
                    continue
                if any(
                    _target_context_compatible(target, row)[0]
                    and _match_option(hit, target, row) is not None
                    for target in options
                ):
                    raw_matches.append(row)
            preselected_record_ids = {
                str(row.get("record_id", "")) for row in _ordered_rows(raw_matches, maximum)
            }
        for row in observed:
            record_id = str(row.get("record_id", ""))
            if not record_id or record_id in consumed:
                continue
            if preselected_record_ids is not None and record_id not in preselected_record_ids:
                continue
            best: dict | None = None
            for target in options:
                if not _material_identity_compatible(target, row):
                    continue
                identity = _match_option(hit, target, row)
                if identity is None:
                    continue
                family_key, identity_fraction = identity
                if str(hit.get("mode")) == "candidate_hit":
                    if explicit_nominations and _norm(row.get("entity_id", "")) not in explicit_nominations:
                        continue
                    candidate_groups.setdefault(
                        (str(target.get("entity_id", "")), str(family_key)), []
                    ).append((row, target, float(identity_fraction)))
                    continue
                quality, reasons = _soft_result_quality(
                    target, row, eligible_evidence_ids, eligible_evidence_by_component,
                    eligible_evidence_entities_by_component, require_evidence,
                )
                if not _localization_identity_is_linked(
                    target, row, eligible_evidence_entities_by_component
                ):
                    reasons = [*reasons, "secondary localization is not linked to the same primary LR identity"]
                    quality = max(0.20, quality - 0.20)
                candidate = {
                    "record_id": record_id,
                    "entity_id": row.get("entity_id"),
                    "source_target_id": target.get("entity_id"),
                    "identity_key": family_key,
                    "identity_fraction": float(identity_fraction) * quality,
                    "quality_fraction": quality,
                    "route": "reference_or_equivalent",
                    "eligibility_failures": reasons,
                }
                if best is None or candidate["identity_fraction"] > best["identity_fraction"]:
                    best = candidate
                if reasons:
                    rejected.append(candidate)
            if best is not None:
                matched_rows.append((row, best))

        # Open scientific route: a result with the right analysis context and
        # auditable quality may earn bounded credit without reproducing a
        # private endpoint name.  Private hits remain the full-credit route;
        # a valid complete-family negative is itself the boundary endpoint.
        if (
            not matched_rows
            and bool(hit.get("allow_context_only_open_route", False))
            and str(hit.get("mode")) in {"theme_hit", "boundary_hit"}
        ):
            for row in observed:
                record_id = str(row.get("record_id", ""))
                if not record_id or record_id in consumed:
                    continue
                for target in options:
                    if not _material_identity_compatible(target, row):
                        continue
                    context_ok, _ = _target_context_compatible(target, row)
                    if not context_ok:
                        continue
                    observed_status = str(row.get("support_status", row.get("status", "")))
                    if str(hit.get("mode")) == "boundary_hit" and observed_status not in {
                        "not_supported", "not_estimable", "not_observable",
                    }:
                        continue
                    open_target = {**target, "evidence_entity_patterns": []}
                    quality, reasons = _soft_result_quality(
                        open_target, row, eligible_evidence_ids, eligible_evidence_by_component,
                        eligible_evidence_entities_by_component, require_evidence,
                    )
                    route_cap = 1.0 if str(hit.get("mode")) == "boundary_hit" else 0.5
                    matched_rows.append((row, {
                        "record_id": record_id,
                        "entity_id": row.get("entity_id"),
                        "source_target_id": target.get("entity_id"),
                        "identity_key": f"OPEN:{_norm(row.get('entity_id', ''))}",
                        "identity_fraction": route_cap * quality,
                        "quality_fraction": quality,
                        "route": "open",
                        "eligibility_failures": reasons,
                    }))
                    break
        # Candidate families may be supported jointly by one row per cohort or
        # scenario.  Requiring one redundant synthesis row to cite every
        # upstream group turns a correct multi-material analysis into zero.
        # Aggregate only rows with the same submitted candidate identity; the
        # numeric/design gates of every cited upstream record remain intact.
        if str(hit.get("mode")) == "candidate_hit":
            allowed_group_keys = set(candidate_groups)
            if not explicit_nominations and len(candidate_groups) > maximum:
                # Apply the nomination bound before the hit-specific
                # qualification test.  Otherwise an exhaustive dump can scan
                # past every failed top candidate until some low-ranked row
                # happens to satisfy the private hit predicate.
                def group_priority(item):
                    key, members = item
                    ranks = [_float(row.get("rank")) for row, _, _ in members]
                    finite = [value for value in ranks if value is not None]
                    return (max(finite) if finite else float("inf"), str(key))

                allowed_group_keys = {
                    key for key, _ in sorted(candidate_groups.items(), key=group_priority)[:maximum]
                }
            for (target_id, family_key), members in candidate_groups.items():
                if (target_id, family_key) not in allowed_group_keys:
                    continue
                if family_key in consumed_candidate_identities:
                    continue
                ordered_members = sorted(
                    members,
                    key=lambda item: (
                        float(item[0].get("rank"))
                        if item[0].get("rank") is not None else float("inf"),
                        str(item[0].get("record_id", "")),
                    ),
                )
                representative, target, identity_fraction = ordered_members[0]
                aggregate = dict(representative)
                aggregate_evidence = {
                    str(value)
                    for row, _, _ in ordered_members
                    for value in row.get("evidence_ids", [])
                }
                aggregate_evidence.update(
                    str(row.get("record_id", ""))
                    for row, _, _ in ordered_members
                    if bool(row.get("process_backed", False))
                )
                aggregate["evidence_ids"] = sorted(value for value in aggregate_evidence if value)
                eligibility_target = target
                if (
                    (
                        bool(hit.get("accept_any_evidence_backed_candidate", False))
                        or (
                            not bool(target.get("reference_pool_is_exhaustive", True))
                            and str(target.get("scoring_mode", ""))
                                in {"candidate_family", "conditional_localization"}
                        )
                    )
                    and (
                        target.get("evidence_entity_patterns")
                        or target.get("evidence_components")
                        or target.get("required_evidence_groups")
                    )
                ):
                    # Reference members are examples, not the only identities
                    # whose upstream rows can qualify.  For an equivalent
                    # novel candidate, bind evidence to the submitted identity
                    # itself instead of requiring it to look like one of the
                    # private examples.
                    eligibility_target = {
                        **target,
                        "evidence_entity_patterns": [str(representative.get("entity_id", ""))],
                    }
                quality, reasons = _soft_result_quality(
                    eligibility_target, aggregate, eligible_evidence_ids, eligible_evidence_by_component,
                    eligible_evidence_entities_by_component, require_evidence,
                )
                quality_ok, quality_failures = _candidate_group_quality(
                    hit.get("candidate_group_rule"), ordered_members, observed
                )
                if not quality_ok:
                    reasons = [*reasons, *quality_failures]
                    quality = max(0.20, quality * 0.60)
                detail = {
                    "record_id": str(representative.get("record_id", "")),
                    "member_record_ids": [
                        str(row.get("record_id", "")) for row, _, _ in ordered_members
                    ],
                    "entity_id": representative.get("entity_id"),
                    "source_target_id": target_id,
                    "identity_key": family_key,
                    "identity_fraction": identity_fraction * quality,
                    "quality_fraction": quality,
                    "eligibility_failures": reasons,
                }
                matched_rows.append((representative, detail))
                if reasons:
                    rejected.append(detail)

        # The nomination cap belongs to this scientific hit type.  Unrelated
        # rows in the same result atom cannot crowd a later key hit out of the
        # window.  Among records that actually match this hit, rank and then
        # record_id determine the bounded nomination set.
        ordered_matches = sorted(
            matched_rows,
            key=lambda item: (
                float(item[0].get("rank")) if item[0].get("rank") is not None else float("inf"),
                str(item[0].get("record_id", "")),
            ),
        )[:maximum]
        for _, best in ordered_matches:
            previous = candidates.get(str(best["identity_key"]))
            if previous is None or float(best["identity_fraction"]) > float(previous["identity_fraction"]):
                candidates[str(best["identity_key"])] = best

        selected = sorted(
            candidates.values(),
            key=lambda item: (-float(item["identity_fraction"]), str(item["record_id"])),
        )[:required]
        fraction = min(1.0, sum(float(item["identity_fraction"]) for item in selected) / required)
        earned = points * fraction
        total += earned
        for item in selected:
            consumed.add(str(item["record_id"]))
            consumed_candidate_identities.add(str(item["identity_key"]))
            for member_id in item.get("member_record_ids", []):
                consumed.add(str(member_id))
            eligible_record_ids.append(str(item["record_id"]))
            eligible_record_targets[str(item["record_id"])] = str(item["source_target_id"])
            eligible_record_hits[str(item["record_id"])] = hit_id
        (passed if fraction >= 1.0 else failed).append(f"{hit_id}: {len(selected)}/{required}")
        detail_by_index[original_index] = {
            "hit_id": hit_id,
            "mode": hit.get("mode"),
            "points_possible": points,
            "points_earned": earned,
            "required_distinct_hits": required,
            "selected_hits": selected,
            "selected_route": (
                selected[0].get("route", "reference_or_equivalent")
                if selected else None
            ),
            "rejected_candidates": rejected[:20],
            "reference_pool_is_exhaustive": False,
        }

    details = [detail_by_index[index] for index in range(len(hit_atoms))]
    score = min(atom.points, total)
    status = "scored" if abs(score - atom.points) < 1e-9 else ("partial" if score > 0 else "failed")
    return AtomScore(
        atom.atom_id, atom.module, atom.kind, atom.points, score, status,
        passed=passed, failed=failed,
        diagnostics={
            "hit_atoms": details,
            "eligible_record_ids": sorted(set(eligible_record_ids)),
            "eligible_record_targets": eligible_record_targets,
            "eligible_record_hits": eligible_record_hits,
            "matching_policy": "explicit_key_hits_nonexhaustive_reference_pool",
        },
    )


def _conclusion_row_matches_module(row: dict, atom: AtomDefinition) -> bool:
    """Keep conclusion identity local without requiring private wording.

    Stage/module identity is part of the scientific object being scored, not a
    formatting gate.  Cross-stage synthesis must be explicitly submitted as S;
    an A claim cannot silently stand in for an unperformed D, V, or S stage.
    """
    explicit_atom_ids = {
        str(value)
        for value in row.get("candidate_atom_ids", [])
        if str(value)
    }
    if row.get("atom_id"):
        explicit_atom_ids.add(str(row["atom_id"]))
    if explicit_atom_ids:
        return atom.atom_id in explicit_atom_ids

    stage = str(row.get("stage", "")).strip().upper().replace("-", "_")
    if not stage:
        return False
    allowed = {
        "A": {"A"},
        "B": {"B", "AB"},
        "C": {"C"},
        "R": {"R"},
        "D": {"D", "D_BLIND", "D_DECODE"},
        "E": {"E"},
        "V": {"V"},
        "S": {"S", "SYNTHESIS", "FINAL"},
    }
    return stage in allowed.get(atom.module.upper(), {atom.module.upper()})


def score_conclusion_hit_atom(
    atom: AtomDefinition,
    submission: dict,
    reference: dict,
    eligible_evidence_ids: set[str] | None = None,
    eligible_evidence_by_group: dict[str, set[str]] | None = None,
) -> AtomScore:
    claim_atoms = reference.get("claim_atoms", [])
    claims = {str(claim.get("claim_id")): claim for claim in reference.get("conclusions", [])}
    if not claim_atoms:
        return AtomScore(
            atom.atom_id, atom.module, atom.kind, atom.points, 0.0, "unavailable",
            failed=["private key-claim atoms are not configured"],
        )
    consumed: set[str] = set()
    passed: list[str] = []
    failed: list[str] = []
    details: list[dict] = []
    eligible_claims: list[str] = []
    total = 0.0
    all_rows = [
        row for row in submission.get("conclusions", [])
        if _conclusion_row_matches_module(row, atom)
    ]
    selected_routes: list[str] = []
    for hit in claim_atoms:
        hit_id = str(hit.get("hit_id"))
        points = float(hit.get("points", 0.0))
        options = [claims[value] for value in hit.get("source_claim_ids", []) if value in claims]
        best_score = 0.0
        best_report: AtomScore | None = None
        best_record_id = ""
        for option in options:
            required = [str(value) for value in option.get("required_terms", [])]
            threshold = float(option.get("minimum_structured_term_fraction", 0.67))
            plausible: list[tuple[dict, float]] = []
            for row in all_rows:
                if str(row.get("record_id", "")) in consumed:
                    continue
                structured_text = " ".join(str(row.get(key, "")) for key in (
                    "subject_type", "subject_id", "relation", "object_type", "object_id",
                    "direction", "support_status", "evidence_level", "conflict_status",
                ))
                tokens = _semantic_tokens(structured_text)
                hits = [
                    bool(term_tokens) and term_tokens.issubset(tokens)
                    for term in required
                    for term_tokens in [_semantic_tokens(term)]
                ]
                semantic = sum(hits) / len(hits) if hits else 1.0
                if semantic > 0:
                    plausible.append((row, semantic))
            maximum = max(1, int(hit.get("maximum_nominations", 3)))
            # The public stage/type nomination budget already prevents
            # enumeration attacks.  Inside one key-claim hit, rank the
            # bounded records by their structured semantic coverage instead
            # of file order; otherwise several earlier weak matches can
            # deterministically crowd out a later exact, evidenced claim.
            plausible.sort(
                key=lambda item: (-item[1], str(item[0].get("record_id", "")))
            )
            for row, _ in plausible[:maximum]:
                local_submission = dict(submission)
                local_submission["conclusions"] = [row]
                local_atom = replace(atom, points=points)
                report = score_conclusion_atom(
                    local_atom,
                    local_submission,
                    {**reference, "conclusions": [option]},
                    eligible_evidence_ids,
                    eligible_evidence_by_group,
                )
                if report.score > best_score:
                    best_score = report.score
                    best_report = report
                    best_record_id = str(row.get("record_id", ""))
        selected_route = "reference_or_equivalent" if best_score > 0 else ""
        if best_score <= 0:
            # Open synthesis route: independently evidenced, structured and
            # appropriately bounded reasoning receives limited credit even
            # when it does not reuse private reference wording.
            open_rows = [
                row for row in all_rows
                if str(row.get("record_id", "")) not in consumed
            ]
            for row in open_rows[:max(1, int(hit.get("maximum_nominations", 3)))]:
                fields = (
                    "subject_type", "subject_id", "relation", "object_type", "object_id",
                    "direction", "support_status", "evidence_level", "conflict_status",
                )
                structure = sum(bool(str(row.get(field, "")).strip()) for field in fields) / len(fields)
                cited = {str(value) for value in row.get("evidence_ids", [])}
                minimum = max(
                    [int(option.get("minimum_evidence_records", 1)) for option in options] or [1]
                )
                evidence = min(1.0, len(cited.intersection(eligible_evidence_ids or set())) / minimum)
                scope = str(row.get("causal_scope", ""))
                bounded = scope in {"observation", "association", "experimental_response"}
                alternatives = row.get("alternative_explanations")
                competing = isinstance(alternatives, list)
                open_quality = 0.35 * structure + 0.35 * evidence + 0.15 * float(bounded) + 0.15 * float(competing)
                open_score = points * 0.5 * open_quality
                if open_score > best_score:
                    best_score = open_score
                    best_record_id = str(row.get("record_id", ""))
                    selected_route = "structured_evidence_chain"
        matched_ids = [best_record_id] if best_score > 0 and best_record_id else []
        if matched_ids:
            consumed.add(str(matched_ids[0]))
            eligible_claims.append(str(matched_ids[0]))
        total += best_score
        if selected_route:
            selected_routes.append(selected_route)
        (passed if abs(best_score - points) < 1e-9 else failed).append(f"{hit_id}: {best_score:.3f}/{points:.3f}")
        details.append({
            "hit_id": hit_id,
            "points_possible": points,
            "points_earned": best_score,
            "matched_record_ids": matched_ids,
            "selected_route": selected_route or None,
            "reference_pool_is_exhaustive": False,
        })
    score = min(atom.points, total)
    status = "scored" if abs(score - atom.points) < 1e-9 else ("partial" if score > 0 else "failed")
    return AtomScore(
        atom.atom_id, atom.module, atom.kind, atom.points, score, status,
        passed=passed, failed=failed,
        diagnostics={
            "claim_hits": details,
            "eligible_claim_record_ids": sorted(set(eligible_claims)),
            "matching_policy": "independent_key_claim_hits_nonexhaustive_reference_pool",
            "selected_route": (
                "structured_evidence_chain"
                if "structured_evidence_chain" in selected_routes
                else (selected_routes[0] if selected_routes else None)
            ),
        },
    )

