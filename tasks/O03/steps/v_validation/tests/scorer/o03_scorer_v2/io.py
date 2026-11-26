from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from .registry import ATOMS
from .results import _analysis_kind
from .streaming_io import canonical_entity_candidates
from .statistics import is_difference_group


def _read_jsonl(path: Path) -> tuple[list[dict], list[dict]]:
    records = []
    issues = []
    with path.open(encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except Exception as exc:
                issues.append({"scope": "results_row", "line": line_number,
                               "message": f"invalid JSON: {type(exc).__name__}: {exc}"})
                continue
            if not isinstance(value, dict):
                issues.append({"scope": "results_row", "line": line_number,
                               "message": "row is not a JSON object"})
                continue
            value["_source_line"] = line_number
            records.append(value)
    return records, issues


def _read_process(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_and_load(output: Path, schema: dict) -> tuple[dict, list[str]]:
    fatal_errors: list[str] = []
    local_errors: list[dict] = []
    missing_outputs: list[str] = []
    for name in schema["required_outputs"]:
        path = output / name
        if name == "code":
            if not path.is_dir() or not any(item.is_file() for item in path.rglob("*")):
                missing_outputs.append(name)
                local_errors.append({"scope": "output", "path": name,
                                     "message": "code directory is absent or empty"})
        elif not path.is_file() or path.stat().st_size == 0:
            missing_outputs.append(name)
            local_errors.append({"scope": "output", "path": name,
                                 "message": f"missing or empty required output: {name}"})

    results_path = output / "results.jsonl"
    if not results_path.is_file() or results_path.stat().st_size == 0:
        fatal_errors.append("core results.jsonl is absent or empty")
        records = []
    else:
        try:
            records, parse_issues = _read_jsonl(results_path)
            local_errors.extend(parse_issues)
        except Exception as exc:
            fatal_errors.append(f"core results parse error: {type(exc).__name__}: {exc}")
            records = []
        if not records and not fatal_errors:
            fatal_errors.append("core results.jsonl contains no parseable object records")

    process_path = output / "process_values.csv.gz"
    if not process_path.is_file() or process_path.stat().st_size == 0:
        process_rows = []
    else:
        try:
            process_rows = _read_process(process_path)
        except Exception as exc:
            process_rows = []
            local_errors.append({"scope": "process_file", "path": "process_values.csv.gz",
                                 "message": f"process table parse error: {type(exc).__name__}: {exc}"})

    common = set(schema["results_jsonl"]["common_required"])
    type_specs = schema["results_jsonl"]["record_types"]
    allowed_stages = set(schema["results_jsonl"].get("stage_values", []))
    allowed_status = set(schema["results_jsonl"].get("status_values", []))
    candidate_records: list[tuple[int, dict]] = []
    for index, row in enumerate(records, 1):
        line_number = int(row.pop("_source_line", index))
        row_errors: list[str] = []
        missing = sorted(common - set(row))
        record_type = str(row.get("record_type", ""))
        if record_type not in type_specs:
            row_errors.append(f"unknown record_type {record_type!r}")
            local_errors.append({"scope": "results_row", "line": line_number,
                                 "record_id": row.get("record_id"), "message": "; ".join(row_errors)})
            continue
        missing += sorted(set(type_specs[record_type]["required"]) - set(row))
        if missing:
            row_errors.append(f"missing {sorted(set(missing))}")
        record_id = str(row.get("record_id", ""))
        if not record_id:
            row_errors.append("empty record_id")
        if allowed_stages and str(row.get("stage")) not in allowed_stages:
            row_errors.append(f"invalid stage {row.get('stage')!r}")
        if allowed_status and str(row.get("status")) not in allowed_status:
            row_errors.append(f"invalid status {row.get('status')!r}")
        if not isinstance(row.get("evidence_ids"), list):
            row_errors.append("evidence_ids must be a list")
        if record_type == "annotation":
            if not isinstance(row.get("supporting_markers"), list) or not isinstance(row.get("contradicting_markers"), list):
                row_errors.append("annotation marker fields must be lists")
        elif record_type == "result":
            allowed_direction = set(type_specs[record_type].get("direction_values", []))
            if allowed_direction and str(row.get("direction")) not in allowed_direction:
                row_errors.append(f"invalid direction {row.get('direction')!r}")
        elif record_type == "conclusion":
            allowed_scope = set(type_specs[record_type].get("causal_scope_values", []))
            if allowed_scope and str(row.get("causal_scope")) not in allowed_scope:
                row_errors.append(f"invalid causal_scope {row.get('causal_scope')!r}")
            allowed_claim_scope = set(type_specs[record_type].get("claim_scope_values", []))
            if allowed_claim_scope and str(row.get("claim_scope")) not in allowed_claim_scope:
                row_errors.append(f"invalid claim_scope {row.get('claim_scope')!r}")
            allowed_level = set(type_specs[record_type].get("evidence_level_values", []))
            if allowed_level and str(row.get("evidence_level")) not in allowed_level:
                row_errors.append(f"invalid evidence_level {row.get('evidence_level')!r}")
            allowed_conflict = set(type_specs[record_type].get("conflict_status_values", []))
            if allowed_conflict and str(row.get("conflict_status")) not in allowed_conflict:
                row_errors.append(f"invalid conflict_status {row.get('conflict_status')!r}")
            if not isinstance(row.get("alternative_explanations"), list):
                row_errors.append("alternative_explanations must be a list")
        if row_errors:
            local_errors.append({"scope": "results_row", "line": line_number,
                                 "record_id": record_id, "message": "; ".join(row_errors)})
            continue
        candidate_records.append((line_number, row))

    # Duplicate primary keys are an attack surface.  Quarantine every member
    # of a conflicting key rather than accepting whichever row happened to be
    # parsed first or last.
    record_locations: dict[str, list[int]] = {}
    for line_number, row in candidate_records:
        record_locations.setdefault(str(row["record_id"]), []).append(line_number)
    duplicate_record_ids = {
        record_id for record_id, locations in record_locations.items()
        if len(locations) > 1
    }
    for record_id in sorted(duplicate_record_ids):
        local_errors.append({
            "scope": "results_duplicate_key",
            "record_id": record_id,
            "lines": record_locations[record_id],
            "message": "all rows with this duplicate record_id were quarantined",
        })
    valid_records = [
        row for _, row in candidate_records
        if str(row["record_id"]) not in duplicate_record_ids
    ]
    if records and not valid_records:
        fatal_errors.append("core results.jsonl contains no schema-valid nonconflicting records")
    record_ids = {str(row["record_id"]) for row in valid_records}
    result_record_ids = {
        str(row["record_id"]) for row in valid_records
        if str(row.get("record_type")) == "result"
    }

    expected_columns = schema["process_values_csv_gz"]["columns"]
    if process_rows:
        absent = sorted(set(expected_columns) - set(process_rows[0]))
        if absent:
            local_errors.append({"scope": "process_file", "path": "process_values.csv.gz",
                                 "message": f"missing columns: {absent}"})
            process_rows = []
    candidate_process_rows: list[tuple[int, dict, tuple[str, ...]]] = []
    for index, row in enumerate(process_rows, 2):
        row_errors: list[str] = []
        if str(row.get("record_id", "")) not in result_record_ids:
            row_errors.append("record_id must link to one valid result record")
        if _truth(row.get("observable", True)):
            try:
                value = float(row.get("value", ""))
            except (TypeError, ValueError):
                row_errors.append("observable value is not numeric")
            else:
                if value != value or value in (float("inf"), float("-inf")):
                    row_errors.append("observable value is not finite")
        if row_errors:
            local_errors.append({"scope": "process_row", "line": index,
                                 "record_id": row.get("record_id"), "message": "; ".join(row_errors)})
            continue
        process_key = tuple(str(row.get(field, "")) for field in (
            "record_id", "entity_id", "unit_id", "pair_id", "block_id",
            "group", "time", "value_role", "feature_id", "stratum_id",
        ))
        candidate_process_rows.append((index, row, process_key))
    process_locations: dict[tuple[str, ...], list[int]] = {}
    for line_number, _, key in candidate_process_rows:
        process_locations.setdefault(key, []).append(line_number)
    duplicate_process_keys = {
        key for key, locations in process_locations.items() if len(locations) > 1
    }
    for key in sorted(duplicate_process_keys):
        local_errors.append({
            "scope": "process_duplicate_key",
            "key": list(key),
            "lines": process_locations[key],
            "message": "all rows with this duplicate process key were quarantined",
        })
    valid_process_rows = [
        row for _, row, key in candidate_process_rows
        if key not in duplicate_process_keys
    ]

    artifact_manifest = {}
    for name in ("results.jsonl", "process_values.csv.gz", "final_report.md"):
        path = output / name
        if path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            artifact_manifest[name] = {
                "sha256": digest.hexdigest(),
                "size_bytes": path.stat().st_size,
            }
    result_key_digest = hashlib.sha256()
    for record_id in sorted(record_ids):
        result_key_digest.update(record_id.encode("utf-8") + b"\n")
    process_key_digest = hashlib.sha256()
    valid_process_keys = sorted(
        tuple(str(row.get(field, "")) for field in (
            "record_id", "entity_id", "unit_id", "pair_id", "block_id",
            "group", "time", "value_role", "feature_id", "stratum_id",
        ))
        for row in valid_process_rows
    )
    for key in valid_process_keys:
        process_key_digest.update("|".join(key).encode("utf-8") + b"\n")
    artifact_manifest["scored_row_keys"] = {
        "result_key_count": len(record_ids),
        "result_key_sha256": result_key_digest.hexdigest(),
        "process_key_count": len(valid_process_rows),
        "process_key_sha256": process_key_digest.hexdigest(),
    }
    return {
        "records": valid_records,
        "process_rows": valid_process_rows,
        "validation": {
            "fatal_errors": fatal_errors,
            "local_errors": local_errors,
            "missing_outputs": missing_outputs,
            "valid_record_count": len(valid_records),
            "valid_process_row_count": len(valid_process_rows),
            "quarantined_record_ids": sorted(duplicate_record_ids),
            "quarantined_process_key_count": len(duplicate_process_keys),
            "artifact_manifest": artifact_manifest,
        },
    }, fatal_errors


def _truth(value: object) -> bool:
    return str(value).strip().lower() not in {"", "0", "false", "no", "none", "nan"}


def _canonical_annotation_level(scope: object, parent_label: object) -> str:
    value = str(scope or "").strip().lower().replace("-", "_")
    if value in {"primary", "primary_lineage", "lineage", "major_lineage", "compartment"}:
        return "primary"
    if value in {"secondary", "secondary_state", "state", "substate", "lineage_state"}:
        return "secondary"
    # A parent label is evidence of a nested state only when the scope did not
    # explicitly identify a primary lineage/compartment.
    if str(parent_label or "").strip():
        return "secondary"
    return value


def to_internal(loaded: dict, private_reference: dict) -> dict:
    records = loaded["records"]
    process_records = loaded.get("family_records") or records
    process_rows = loaded["process_rows"]
    rank_audit_rows = loaded.get("rank_audit_rows", [])
    rank_audits_by_family: dict[str, list[dict]] = {}
    for row in rank_audit_rows:
        rank_audits_by_family.setdefault(str(row.get("_submitted_family_key", "")), []).append(row)
    member_stats_by_family = {
        str(row.get("family_key", "")): row
        for row in loaded.get("evidence_bundle_members", [])
    }
    by_record: dict[str, list[dict]] = {}
    for row in process_rows:
        converted = dict(row)
        converted["observable"] = _truth(row.get("observable", True))
        for key in ("value", "numerator", "denominator"):
            try:
                converted[key] = float(row[key]) if str(row.get(key, "")).strip() else None
            except ValueError:
                converted[key] = None
        raw_time = row.get("time", "")
        if str(raw_time).strip():
            try:
                converted["time"] = float(raw_time)
            except (TypeError, ValueError):
                # Time is a structural field as well as a possible numeric
                # covariate.  Encodings such as `6h-0h` must remain lossless.
                converted["time"] = str(raw_time).strip()
        else:
            converted["time"] = None
        by_record.setdefault(str(row.get("record_id", "")), []).append(converted)

    submission = {"annotations": [], "results": [], "conclusions": [], "process": [], "raw_records": records}
    state_aliases: dict[str, dict[str, str]] = {}
    for atom_id, atom in ATOMS.items():
        if atom.kind != "annotation":
            continue
        ref = private_reference.get("atoms", {}).get(atom_id, {})
        stage = str(ref.get("selector", {}).get("stage", atom.module))
        anchors = ref.get("anchors", [])
        for row in records:
            if str(row.get("record_type")) != "annotation" or str(row.get("stage")) != stage:
                continue
            declared_markers = {str(value).upper() for value in row.get("supporting_markers", [])}
            valid_marker_statistics: dict[str, dict] = {}
            for statistic in row.get("marker_statistics", []):
                if str(statistic.get("role", "")) != "supporting":
                    continue
                try:
                    valid = (
                        float(statistic.get("effect")) > 0
                        and float(statistic.get("pct_in")) > float(statistic.get("pct_out"))
                        and float(statistic.get("q_value")) <= 0.10
                    )
                except (TypeError, ValueError):
                    valid = False
                if valid:
                    valid_marker_statistics[str(statistic.get("gene", "")).upper()] = statistic
            markers = declared_markers.intersection(valid_marker_statistics)
            # Legacy/publicly valid submissions may provide the exact marker
            # panel used for annotation without duplicating per-marker test
            # statistics.  Such declarations are useful for semantic routing
            # but are weaker than auditable quantitative marker evidence.
            # Require at least two anchor markers, inspect only the bounded
            # leading panel, and never let this bridge create full annotation
            # credit by itself.
            declared_panel = {
                str(value).upper() for value in row.get("supporting_markers", [])[:20]
            }
            annotation_level = _canonical_annotation_level(
                row.get("scope", ""), row.get("parent_label", "")
            )
            best_anchor = ""; best_score = 0.0
            for anchor in anchors:
                accepted_levels = {
                    str(value) for value in anchor.get(
                        "accepted_annotation_levels",
                        [anchor.get("annotation_level")],
                    ) if value is not None
                }
                if accepted_levels and annotation_level not in accepted_levels:
                    continue
                positives = {str(value).upper() for value in anchor.get("positive_markers", [])}
                alternatives = {str(value).upper() for value in anchor.get("alternative_markers", [])}
                score = len(markers & positives) + 0.5 * len(markers & alternatives)
                if not markers:
                    declared_hits = len(declared_panel & positives)
                    declared_alternatives = len(declared_panel & alternatives)
                    if declared_hits >= 2:
                        score = declared_hits + 0.25 * declared_alternatives
                minimum = max(1, int(anchor.get("minimum_positive", 1)))
                required_bridge = max(2, minimum)
                if score >= (minimum if markers else required_bridge) and score > best_score:
                    best_score = score; best_anchor = str(anchor.get("anchor_id", ""))
            if best_anchor and best_score > 0:
                for key in (row.get("cluster_id"), row.get("label")):
                    if str(key or "").strip():
                        state_aliases.setdefault(stage, {})[str(key)] = best_anchor

    def enrich_semantics(row: dict) -> dict:
        item = dict(row)
        stage_map = state_aliases.get(str(row.get("stage", "")), {})
        aliases: set[str] = set()
        entity = str(row.get("entity_id", ""))
        scope = str(row.get("scope", ""))
        for submitted, semantic in stage_map.items():
            if submitted == entity:
                aliases.add(semantic)
            # Cluster labels are often short integers ("0", "2") or terse
            # state IDs ("F4").  Replacing arbitrary substrings corrupts
            # database years, accessions and gene names.  State propagation
            # is valid only when the submitted label occupies a complete
            # pipe-delimited identity segment.
            entity_parts = entity.split("|")
            if submitted and submitted in entity_parts:
                aliases.add("|".join(
                    semantic if part == submitted else part for part in entity_parts
                ))
            if submitted == scope:
                item["_semantic_scope"] = semantic
        if aliases:
            item["_semantic_entity_aliases"] = sorted(aliases)
        return item

    process_records = [enrich_semantics(row) for row in process_records]

    # Admission routing is deliberately answer-blind.  A schema-valid result
    # survives when its public stage and analysis class are compatible with a
    # result atom.  Biological identity is evaluated later by the hit scorer;
    # using private target names here silently discarded novel but legitimate
    # findings before their evidence could even be assessed.
    result_atom_candidates: dict[str, list[str]] = {}
    for row in records:
        if str(row.get("record_type", "")) != "result":
            continue
        observed_kind = _analysis_kind(row.get("analysis_type"))
        candidates: list[str] = []
        for candidate_atom_id, candidate_atom in ATOMS.items():
            if candidate_atom.kind != "result":
                continue
            candidate_reference = private_reference["atoms"].get(candidate_atom_id, {})
            selector = candidate_reference.get("selector", {})
            if selector.get("stage") and str(row.get("stage")) != str(selector["stage"]):
                continue
            if selector.get("analysis_type") and str(row.get("analysis_type")) != str(selector["analysis_type"]):
                continue
            allowed_kinds = {
                str(value)
                for target in candidate_reference.get("targets", [])
                for value in target.get("allowed_analysis_kinds", [])
            }
            if allowed_kinds and observed_kind not in allowed_kinds:
                continue
            candidates.append(candidate_atom_id)
        if candidates:
            result_atom_candidates[str(row.get("record_id", ""))] = sorted(candidates)
    family_record_by_id = {
        str(row.get("record_id", "")): row
        for row in process_records
        if str(row.get("record_type", "")) == "result"
    }
    cited_ids = {
        str(evidence_id)
        for row in records
        for evidence_id in row.get("evidence_ids", [])
    }
    family_groups: dict[tuple[str, str, str, str], list[dict]] = {}
    for row in process_records:
        if str(row.get("record_type")) != "result":
            continue
        key = (
            str(row.get("stage", "")),
            str(row.get("analysis_type", "")),
            # Family assignment must preserve the submitter's literal scope.
            # Marker-derived semantic aliases are useful for result matching,
            # but collapsing a secondary state to its parent lineage here can
            # make that state steal an aggregate process component.
            str(row.get("scope", "")),
            str(row.get("family_id", "")),
        )
        family_groups.setdefault(key, []).append(row)

    def suffix_tokens(entity: str) -> set[str]:
        parts = str(entity).split("|")
        text = "|".join(parts[1:]) if len(parts) > 1 else str(entity)
        return {token.upper() for token in text.replace("__", "|").replace("_", "|").split("|") if token}

    def canonical_scope(value: object) -> str:
        """Normalize only structural scope aliases used by submitted families."""
        text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "all_fibroblast": "fibroblast",
            "total_fibroblast": "fibroblast",
            "fibroblast_aggregate": "fibroblast",
            "ecm_rich_state": "ecm_rich",
            "all_endothelial": "endothelial",
            "all_mural": "mural",
        }
        return aliases.get(text, text)

    def canonical_pathway_library(value: object) -> str:
        """Normalize the three public pathway-library names only.

        Family IDs may be either a bare library name or a pipe-delimited
        technical key.  Library identity is not a fuzzy biological label: a
        Hallmark component must not consume a GO family simply because both
        happen to use the same cell scope.
        """
        text = str(value or "").split("|")[-1].strip().lower()
        text = text.replace("msigdb_", "").replace("biological_process", "bp")
        text = text.replace("-", "_").replace(" ", "_")
        aliases = {
            "hallmark_2020": "hallmark_2020",
            "go_bp_2023": "go_bp_2023",
            "reactome_2022": "reactome_2022",
        }
        return aliases.get(text, text)

    spec_feature_cache: dict[tuple[str, tuple[str, ...]], dict[str, set]] = {}
    group_feature_cache: dict[int, dict[str, set]] = {}

    def spec_features(spec: dict) -> dict[str, set]:
        component = str(spec.get("component_id", ""))
        family_values = tuple(str(value) for value in spec.get("family_entities", []))
        key = (component, family_values)
        cached = spec_feature_cache.get(key)
        if cached is not None:
            return cached
        cached = {
            "references": {
                canonical_scope(value) for value in family_values if value.strip()
            },
            "reference_libraries": {
                canonical_pathway_library(value.split("|", 2)[1])
                for value in family_values if len(value.split("|", 2)) >= 3
            },
            "reference_scopes": {
                canonical_scope(value.split("|", 1)[0])
                for value in family_values if "|" in value
            },
            "reference_entity_scopes": {
                canonical_scope(value) for value in family_values if value.strip()
            },
            "reference_suffixes": {
                frozenset(suffix_tokens(value)) for value in family_values if suffix_tokens(value)
            },
        }
        spec_feature_cache[key] = cached
        return cached

    def group_features(rows: list[dict]) -> dict[str, set]:
        key = id(rows)
        cached = group_feature_cache.get(key)
        if cached is not None:
            return cached
        semantic_scopes = {
            canonical_scope(row.get("_semantic_scope", ""))
            for row in rows if str(row.get("_semantic_scope", "")).strip()
        }
        raw_submitted = {
            canonical_scope(row.get("entity_id", ""))
            for row in rows if str(row.get("entity_id", "")).strip()
        }
        state_submitted = {
            canonical_scope(candidate)
            for row in rows
            for candidate in canonical_entity_candidates(row)
            if str(candidate).strip()
        }
        submitted_suffixes = {
            frozenset(suffix_tokens(candidate))
            for row in rows for candidate in canonical_entity_candidates(row)
            if suffix_tokens(candidate)
        }
        cached = {
            "semantic_scopes": semantic_scopes,
            "raw_submitted": raw_submitted,
            "state_submitted": state_submitted,
            "submitted_suffixes": submitted_suffixes,
        }
        group_feature_cache[key] = cached
        return cached

    def has_biological_entity_match(spec: dict, rows: list[dict]) -> bool:
        """Prefer an exact structural/marker-backed endpoint match.

        This is deliberately separate from fuzzy token scoring: a broad
        composition family containing the fibroblast row must outrank a
        secondary-state composition family, while a marker-mapped ECM state
        must remain available to the state component.
        """
        references = spec_features(spec)["references"]
        component = str(spec.get("component_id", ""))
        # Semantic marker aliases are needed for the solver-defined state
        # label, but must not let one state row impersonate the aggregate
        # fibroblast endpoint.
        features = group_features(rows)
        submitted = features["state_submitted"] if component == "state" else features["raw_submitted"]
        return bool(references.intersection(submitted))

    def group_score(spec: dict, key: tuple[str, str, str, str], rows: list[dict]) -> float:
        stage, analysis_type, scope, _ = key
        if stage != str(spec.get("match_stage", "")):
            return -1.0
        component = str(spec.get("component_id", ""))
        expected_analysis = component.split("__", 1)[0]
        explicit_analysis_types = {
            str(value).strip().lower()
            for value in spec.get("match_analysis_types", [])
            if str(value).strip()
        }
        if explicit_analysis_types and analysis_type.lower() not in explicit_analysis_types:
            return -1.0
        # State endpoints can have module-specific component names (for
        # example B's ``native_state``).  They are still composition/state
        # analyses and must never be assigned a large communication family
        # merely because both live in the same stage.
        state_components = {"composition", "state", "native_state"}
        if component in state_components and analysis_type not in {
            "composition", "patient_level_test"
        }:
            return -1.0
        if component == "state_excluded":
            if analysis_type not in {"expression", "patient_level_test"}:
                return -1.0
            exclusion_text = "|".join((scope, str(key[3]))).lower().replace("-", "_")
            if not any(token in exclusion_text for token in ("non_state", "state_excluded", "exclude")):
                return -1.0
        accepted_analysis_types = {
            "pathway": {"pathway", "patient_level_test"},
            # decoupler exposes TF activity through ULM/MLM result families;
            # these are TF analyses, not incompatible substitute methods.
            "tf": {"tf", "tf_ulm", "tf_mlm", "patient_level_test"},
            "communication": {"communication", "patient_level_test"},
        }
        if (
            expected_analysis in accepted_analysis_types
            and analysis_type not in accepted_analysis_types[expected_analysis]
        ):
            return -1.0
        annotation_scope_match = False
        if expected_analysis == "pathway":
            reference_libraries = spec_features(spec)["reference_libraries"]
            submitted_library = canonical_pathway_library(key[3])
            if len(reference_libraries) == 1 and submitted_library not in reference_libraries:
                return -1.0
        d_encoded_family = component in {"timecourse", "defect_background"}
        if d_encoded_family and analysis_type not in {
            "exploratory_program_mean_response",
            "coded_program_response",
            "fixed_candidate_program_response",
        }:
            return -1.0
        match_scope = str(spec.get("match_scope", ""))
        score = 0.0
        if annotation_scope_match:
            score += 100.0
        if d_encoded_family:
            score += 50.0
        if scope == component:
            # Most process references use the component_id itself as the
            # public technical scope and therefore omit a redundant
            # match_scope field.
            score += 100.0
        if match_scope and scope == match_scope:
            # An explicit technical component scope is the strongest key.
            # Biological-scope aliases below are only a fallback for otherwise
            # ambiguous families (for example aggregate versus state-specific
            # fibroblast families).  They must not let a generic fibroblast
            # family steal a named pathway/TF/communication component.
            score += 100.0
        # The first field of a pipe-delimited family entity is its biological
        # scope.  Without this preference, aggregate and secondary-state
        # families from the same library have identical suffixes and the
        # lexicographically first state can steal an aggregate component.
        reference_scopes = spec_features(spec)["reference_scopes"]
        if len(reference_scopes) == 1:
            literal_scope = canonical_scope(scope.split("|", 1)[0])
            semantic_scopes = group_features(rows)["semantic_scopes"]
            if literal_scope in reference_scopes:
                score += 40.0
            elif semantic_scopes.intersection(reference_scopes):
                # A marker-backed state alias may bridge arbitrary submitted
                # cluster names, but it must rank below an exact literal scope
                # so a secondary state cannot steal an aggregate component.
                score += 25.0
        # State labels are intentionally solver-defined.  A marker-supported
        # annotation may therefore map an arbitrary cluster label (for
        # example F0_...) to a private biological anchor.  Use that semantic
        # bridge for family assignment without rewriting the submitted key.
        semantic_scopes = group_features(rows)["semantic_scopes"]
        reference_entity_scopes = spec_features(spec)["reference_entity_scopes"]
        if semantic_scopes.intersection(reference_entity_scopes):
            score += 25.0
        scope_tokens = suffix_tokens(scope)
        component_tokens = suffix_tokens(component)
        if scope_tokens and component_tokens:
            score += 4.0 * len(scope_tokens & component_tokens) / len(scope_tokens | component_tokens)
        analysis_tokens = suffix_tokens(analysis_type)
        if analysis_tokens & component_tokens:
            score += 1.0
        reference_suffixes = spec_features(spec)["reference_suffixes"]
        submitted_suffixes = group_features(rows)["submitted_suffixes"]
        if reference_suffixes and submitted_suffixes:
            overlap = len(reference_suffixes & submitted_suffixes)
            score += 10.0 * overlap / max(1, min(len(reference_suffixes), len(submitted_suffixes)))
        # Composition/state families often use solver-defined labels rather
        # than the private canonical endpoint name.  Prefer the family whose
        # literal or marker-derived entity candidates map to the requested
        # biological entity.  This also prevents a secondary-state table from
        # being consumed by the aggregate-composition component merely because
        # both have analysis_type=composition.
        if expected_analysis not in {"pathway", "tf", "communication"}:
            if has_biological_entity_match(spec, rows):
                score += 30.0
        return score

    def assignment_score(spec: dict, stage: str, key: tuple[str, str, str, str], rows: list[dict]) -> float:
        base = group_score({**spec, "match_stage": stage}, key, rows)
        # A biologically matching entity cannot rescue a technically
        # ineligible family (wrong analysis type or missing an explicit
        # state-exclusion scope).
        if base < 0:
            return base
        entity_match = has_biological_entity_match(spec, rows)
        if str(spec.get("design_type", "")) == "relationship":
            submitted = group_features(rows)["raw_submitted"]
            if not any(len(value.split("|")) >= 3 for value in submitted):
                return -1.0
        return base + (1000.0 if entity_match else 0.0)

    for atom_id, atom in ATOMS.items():
        ref = private_reference["atoms"].get(atom_id, {})
        selector = ref.get("selector", {})
        selected = [row for row in records
                    if (not selector.get("stage") or str(row.get("stage")) == str(selector["stage"]))
                    and (not selector.get("record_type") or str(row.get("record_type")) == str(selector["record_type"]))
                    and (not selector.get("analysis_type") or str(row.get("analysis_type")) == str(selector["analysis_type"]))]
        if atom.kind == "conclusion":
            # Scope is a scientific field to be assessed by the claim gates,
            # not a hidden routing default.  Only a scope explicitly frozen in
            # the private selector may exclude a schema-valid conclusion.
            # Otherwise labels such as `module`, `stage_synthesis` and
            # `cross_stage_synthesis` are organizational variants and must not
            # make the record disappear before scoring.
            if selector.get("claim_scope"):
                claim_scope = str(selector["claim_scope"])
                selected = [row for row in selected if str(row.get("claim_scope")) == claim_scope]
        if atom.kind == "annotation":
            for row in selected:
                scope = str(row.get("scope", "")).strip()
                parent_label = str(row.get("parent_label") or "").strip()
                annotation_level = _canonical_annotation_level(scope, parent_label)
                item = dict(row)
                item.update({"atom_id": atom_id, "assigned_label": row.get("label"),
                             "positive_markers": row.get("supporting_markers", []),
                             "negative_markers": row.get("contradicting_markers", []),
                             "marker_statistics": row.get("marker_statistics", []),
                             "annotation_level": annotation_level})
                submission["annotations"].append(item)
        elif atom.kind == "result":
            for row in selected:
                candidate_atom_ids = result_atom_candidates.get(str(row.get("record_id", "")), [])
                if not candidate_atom_ids or atom_id != candidate_atom_ids[0]:
                    continue
                item = dict(row)
                record_id = str(row.get("record_id", ""))
                cited_evidence_ids = [
                    str(value) for value in row.get("evidence_ids", []) if str(value)
                ]
                # Public result IDs identify the nomination; evidence_ids
                # identify the independently auditable family rows.  They are
                # intentionally different namespaces in normal submissions.
                # Prefer a cited family row and retain the legacy same-ID
                # fallback for older compact exporters.
                family_row = next(
                    (
                        family_record_by_id[evidence_id]
                        for evidence_id in cited_evidence_ids
                        if evidence_id in family_record_by_id
                    ),
                    family_record_by_id.get(record_id),
                )
                family_consistent = True
                if family_row is not None:
                    for field in (
                        "entity_id", "analysis_type", "scope", "family_id", "contrast",
                        "direction", "method", "effect", "statistic", "p_value", "q_value",
                        "n_units", "rank", "coverage",
                    ):
                        left = row.get(field)
                        right = family_row.get(field)
                        if field == "coverage":
                            def coverage_value(value):
                                if isinstance(value, str):
                                    try:
                                        parsed = json.loads(value)
                                    except (TypeError, ValueError, json.JSONDecodeError):
                                        parsed = value
                                    value = parsed
                                if isinstance(value, dict):
                                    value = value.get(
                                        "paired_patients",
                                        value.get("n_units", value.get("case", 0) + value.get("reference", 0)
                                                  if "case" in value and "reference" in value else None),
                                    )
                                return float(value)
                            try:
                                equal = abs(coverage_value(left) - coverage_value(right)) <= 1e-10 * max(
                                    1.0, abs(coverage_value(left)), abs(coverage_value(right))
                                )
                            except (TypeError, ValueError):
                                equal = str(left) == str(right)
                        elif field in {
                            "entity_id", "analysis_type", "scope", "family_id", "contrast",
                            "direction", "method",
                        }:
                            equal = str(left) == str(right)
                        else:
                            try:
                                equal = (
                                    left is None and right is None
                                ) or abs(float(left) - float(right)) <= 1e-10 * max(
                                    1.0, abs(float(left)), abs(float(right))
                                )
                            except (TypeError, ValueError):
                                equal = str(left) == str(right)
                        if not equal:
                            family_consistent = False
                            break
                item.update({
                    "atom_id": "",
                    "candidate_atom_ids": candidate_atom_ids,
                    "support_status": row.get("status"),
                    "process_backed": any(
                        evidence_id in by_record for evidence_id in cited_evidence_ids
                    ) or record_id in by_record,
                    "family_record_consistent": family_consistent,
                    "semantic_aliases": enrich_semantics(row).get("_semantic_entity_aliases", []),
                })
                submission["results"].append(item)
        elif atom.kind == "conclusion":
            for row in selected:
                item = dict(row); item["atom_id"] = atom_id
                submission["conclusions"].append(item)
        elif atom.kind == "process":
            specs = list(ref.get("components", []))
            available_groups = sorted(
                (key, rows) for key, rows in family_groups.items()
                if key[0] == atom.module or any(
                    key[0] == str(spec.get("match_stage", atom.module)) for spec in specs
                )
            )
            # Assign all components jointly.  Sequential greedy assignment is
            # order-dependent: an early, weakly matching component can steal
            # the only correct family from a later component.  Dummy columns
            # allow a component to remain unassigned when every real score is
            # non-positive.
            assigned: dict[int, int] = {}
            if specs and available_groups:
                scores = np.zeros((len(specs), len(available_groups) + len(specs)), float)
                for spec_index, spec in enumerate(specs):
                    stage = str(spec.get("match_stage", atom.module))
                    for group_index, (key, group_rows) in enumerate(available_groups):
                        scores[spec_index, group_index] = max(
                            0.0, assignment_score(spec, stage, key, group_rows)
                        )
                spec_rows, group_cols = linear_sum_assignment(-scores)
                for spec_index, group_index in zip(spec_rows, group_cols):
                    if group_index < len(available_groups) and scores[spec_index, group_index] > 0:
                        assigned[int(spec_index)] = int(group_index)
            for spec_index, spec in enumerate(specs):
                stage = str(spec.get("match_stage", atom.module))
                candidate_groups = [
                    (
                        assignment_score(spec, stage, key, group_rows),
                        key,
                        group_rows,
                    )
                    for key, group_rows in family_groups.items()
                    if key[0] == stage
                ]
                candidate_groups.sort(key=lambda item: (-item[0], item[1]))
                selected_group_index = assigned.get(spec_index)
                if selected_group_index is None:
                    submission["process"].append({
                        "atom_id": atom_id,
                        "component_id": spec["component_id"],
                        "observations": [], "reported": [], "record_ids": [],
                        "audit_entity_ids": [],
                    })
                    continue
                selected_key, selected_rows = available_groups[selected_group_index]
                submitted_family_keys = {
                    str(row.get("_submitted_family_key", "")) for row in selected_rows
                    if str(row.get("_submitted_family_key", ""))
                }
                selected_family_key = next(iter(submitted_family_keys), "") if len(submitted_family_keys) == 1 else ""
                assignment_candidates = [
                    {
                        "score": candidate_score,
                        "stage": candidate_key[0],
                        "analysis_type": candidate_key[1],
                        "scope": candidate_key[2],
                        "family_id": candidate_key[3],
                        "biological_entity_match": has_biological_entity_match(spec, candidate_rows),
                    }
                    for candidate_score, candidate_key, candidate_rows in candidate_groups[:3]
                ]
                reported = []
                observations = []
                component_record_ids: set[str] = set()
                submitted_entities: dict[str, dict] = {}
                submitted_entity_rows: dict[str, list[dict]] = {}
                for row in selected_rows:
                    # Keep the submitter's stable entity key so process rows
                    # join losslessly.  Canonical aliases are for matching,
                    # never for silently rewriting primary keys.
                    canonical_entity = str(row.get("entity_id", ""))
                    submitted_entities.setdefault(canonical_entity, row)
                    submitted_entity_rows.setdefault(canonical_entity, []).append(row)
                ranked_entities = sorted(
                    submitted_entities,
                    key=lambda entity: hashlib.sha256(
                        "|".join((selected_key[0], selected_key[1], selected_key[2], entity)).encode("utf-8")
                    ).hexdigest(),
                )
                audit_entities = set(ranked_entities[:64])
                cited_entities = {
                    entity for entity, row in submitted_entities.items()
                    if str(row.get("record_id", "")) in cited_ids
                }
                fixed_method_entities = {
                    submitted_entity
                    for submitted_entity in submitted_entities
                    if any(
                        submitted_entity.casefold() == str(expected).casefold()
                        for expected in spec.get("method_check_entities", [])
                    )
                }
                if str(spec.get("design_type", "")) == "identifiability_audit":
                    required_groups = {
                        str(spec.get("case_label", "case")),
                        str(spec.get("reference_label", "reference")),
                    }
                    minimum = int(spec.get("minimum_units_per_group", 2))
                    complete_entities = []
                    for submitted_entity, family_row in submitted_entities.items():
                        units_by_group: dict[str, set[str]] = {}
                        for value_row in by_record.get(str(family_row.get("record_id", "")), []):
                            if not bool(value_row.get("observable", True)):
                                continue
                            units_by_group.setdefault(str(value_row.get("group", "")), set()).add(
                                str(value_row.get("unit_id", ""))
                            )
                        if all(len(units_by_group.get(group, set())) >= minimum for group in required_groups):
                            complete_entities.append(submitted_entity)
                    # Missingness-only selection is deterministic and does not
                    # select on effects or p-values.  It represents the
                    # complete-case universe needed for the order audit.
                    complete_entities.sort(key=lambda entity: hashlib.sha256(entity.encode("utf-8")).hexdigest())
                    audit_entities = set(complete_entities[:64])
                if bool(spec.get("fixed_method_check_entities", False)):
                    selected_entities = fixed_method_entities
                    audit_entity_ids = fixed_method_entities
                else:
                    # Variable complete families are audited on the
                    # submitter's deterministic SHA subset plus explicitly
                    # cited endpoints.  Pulling in pre-experiment entity IDs
                    # here silently converts a conditional reference family
                    # into a fixed one and creates false missing-row failures
                    # whenever the accepted family universe changes.
                    selected_entities = audit_entities | cited_entities
                    audit_entity_ids = selected_entities
                for canonical_entity, row in submitted_entities.items():
                    entity_family_rows = submitted_entity_rows.get(canonical_entity, [row])
                    value_rows = [
                        value_row
                        for family_row in entity_family_rows
                        for value_row in by_record.get(str(family_row.get("record_id")), [])
                    ]
                    design_type = str(spec.get("design_type", "group_contrast"))
                    audit_rows_usable = True
                    if canonical_entity in selected_entities and design_type not in {
                        "relationship",
                        "identifiability_audit",
                        "sensitivity_summary",
                        "structured_family_summary",
                        "single_replicate_timecourse",
                    }:
                        expected_groups = {str(spec.get("case_label", "case")), str(spec.get("reference_label", "reference"))}
                        observable_rows = [value_row for value_row in value_rows if bool(value_row.get("observable", True))]
                        observed_groups = {str(value_row.get("group", "")) for value_row in observable_rows}
                        difference_encoded = len(observed_groups) == 1 and all(
                            is_difference_group(
                                group, spec.get("case_label", "case"),
                                spec.get("reference_label", "reference"),
                            )
                            for group in observed_groups
                        )
                        if observable_rows and not expected_groups.issubset(observed_groups) and not difference_encoded:
                            audit_rows_usable = False
                    reported.append({"record_id": row.get("record_id"),
                                     "entity_id": canonical_entity, "effect": row.get("effect"),
                                     "statistic": row.get("statistic"), "p_value": row.get("p_value"),
                                     "q_value": row.get("q_value"), "method": row.get("method"),
                                     "semantic_aliases": enrich_semantics(row).get("_semantic_entity_aliases", []),
                                     "observable": row.get("status") not in {"not_observable", "not_estimable"}})
                    component_record_ids.update(
                        str(family_row.get("record_id")) for family_row in entity_family_rows
                    )
                    if canonical_entity in selected_entities and audit_rows_usable:
                        for value_row in value_rows:
                            item = dict(value_row); item["entity_id"] = canonical_entity; observations.append(item)
                submission["process"].append({"atom_id": atom_id, "component_id": spec["component_id"],
                                               "observations": observations, "reported": reported,
                                               "record_ids": sorted(component_record_ids),
                                               "audit_entity_ids": sorted(audit_entity_ids),
                                               "assignment_candidates": assignment_candidates,
                                               "rank_audit": rank_audits_by_family.get(selected_family_key, []),
                                               "rank_manifest": member_stats_by_family.get(selected_family_key, {}),
                                               "submitted_family": {
                                                   "stage": selected_key[0], "analysis_type": selected_key[1],
                                                   "scope": selected_key[2], "family_id": selected_key[3],
                                               }})
    return submission
