from __future__ import annotations

from .models import ScoreReport
from .process import score_process_atom
from .registry import ATOMS
from .results import score_annotation_atom, score_conclusion_atom, score_result_atom
from .hit_scoring import score_conclusion_hit_atom, score_result_hit_atom


def score_submission(submission: dict, private_reference: dict) -> ScoreReport:
    reference_atoms = private_reference.get("atoms", {})
    scores_by_id = {}
    eligible_process_by_module: dict[str, set[str]] = {}
    eligible_process_by_component: dict[str, dict[str, set[str]]] = {}
    eligible_process_entities_by_component: dict[str, dict[str, dict[str, str]]] = {}
    eligible_result_by_module: dict[str, set[str]] = {}
    eligible_result_groups_by_module: dict[str, dict[str, set[str]]] = {}

    # Process evidence is scored first.  Its diagnostics provide the exact
    # record IDs whose design, primary test, and correction all passed.  Only
    # directly dependent result records may inherit that eligibility.
    for atom_id, atom in ATOMS.items():
        if atom.kind != "process":
            continue
        reference = dict(reference_atoms.get(atom_id, {}))
        reference["unit_contract"] = private_reference.get("unit_contract", {}).get(atom.module)
        score = score_process_atom(atom, submission, reference)
        scores_by_id[atom_id] = score
        for component_id, component in score.diagnostics.items():
            if isinstance(component, dict) and component.get("eligible_for_results"):
                # Numeric method/Q evidence is entity-local.  A malformed row
                # must not erase unrelated valid findings, and a valid row
                # must not lend eligibility to a corrupted neighbour.
                record_ids = {
                    str(value) for value in component.get(
                        "eligible_record_ids", component.get("record_ids", [])
                    )
                }
                eligible_process_by_module.setdefault(atom.module, set()).update(record_ids)
                eligible_process_by_component.setdefault(atom.module, {}).setdefault(
                    str(component_id), set()
                ).update(record_ids)
                eligible_process_entities_by_component.setdefault(atom.module, {}).setdefault(
                    str(component_id), {}
                ).update({
                    str(record_id): str(entity_id)
                    for record_id, entity_id in component.get("record_entities", {}).items()
                    if str(record_id) in record_ids
                })

    for atom_id, atom in ATOMS.items():
        if atom.kind not in {"annotation", "result"}:
            continue
        reference = reference_atoms.get(atom_id, {})
        if atom.kind == "annotation":
            score = score_annotation_atom(atom, submission, reference)
        else:
            reference = dict(reference)
            dependency_map = private_reference.get("result_evidence_components", {}).get(atom_id, {})
            if dependency_map and reference.get("targets"):
                reference["targets"] = [
                    {
                        **target,
                        "evidence_components": dependency_map.get(
                            str(target.get("entity_id", "")), target.get("evidence_components", [])
                        ),
                    }
                    for target in reference["targets"]
                ]
            evidence = (
                set().union(*eligible_result_by_module.values())
                if atom.module == "S"
                else eligible_process_by_module.get(atom.module, set())
            )
            if atom.module == "S":
                component_evidence = {
                    key: set().union(*(
                        groups.get(key, set())
                        for groups in eligible_result_groups_by_module.values()
                    ))
                    for key in set().union(*(
                        set(groups) for groups in eligible_result_groups_by_module.values()
                    ))
                } if eligible_result_groups_by_module else {}
                component_entities = {}
            else:
                component_evidence = eligible_process_by_component.get(atom.module, {})
                component_entities = eligible_process_entities_by_component.get(atom.module, {})
            result_scorer = score_result_hit_atom if reference.get("hit_atoms") else score_result_atom
            score = result_scorer(
                atom, submission, reference, evidence, component_evidence, component_entities,
            )
            newly_eligible = {
                str(value) for value in score.diagnostics.get("eligible_record_ids", [])
            }
            eligible_result_by_module.setdefault(atom.module, set()).update(newly_eligible)
            for record_id, entity_id in score.diagnostics.get("eligible_record_targets", {}).items():
                module_groups = eligible_result_groups_by_module.setdefault(atom.module, {})
                module_groups.setdefault(atom.atom_id, set()).add(str(record_id))
                module_groups.setdefault(f"{atom.atom_id}:{entity_id}", set()).add(str(record_id))
            for record_id, hit_id in score.diagnostics.get("eligible_record_hits", {}).items():
                module_groups = eligible_result_groups_by_module.setdefault(atom.module, {})
                module_groups.setdefault(f"{atom.atom_id}:{hit_id}", set()).add(str(record_id))
        scores_by_id[atom_id] = score

    # Conclusions may cite any submitted scientific result.  Result scoring
    # and process scoring remain independent quality assessments; they no
    # longer issue a binary permission token for interpretation.
    submitted_result_by_module: dict[str, set[str]] = {}
    submitted_result_groups_by_module: dict[str, dict[str, set[str]]] = {}
    for row in submission.get("results", []):
        record_id = str(row.get("record_id", ""))
        if not record_id:
            continue
        candidate_atoms = row.get("candidate_atom_ids")
        atom_ids = (
            [str(value) for value in candidate_atoms]
            if isinstance(candidate_atoms, list)
            else [str(row.get("atom_id", ""))]
        )
        for result_atom_id in atom_ids:
            result_atom = ATOMS.get(result_atom_id)
            if result_atom is None or result_atom.kind != "result":
                continue
            submitted_result_by_module.setdefault(result_atom.module, set()).add(record_id)
            groups = submitted_result_groups_by_module.setdefault(result_atom.module, {})
            groups.setdefault(result_atom_id, set()).add(record_id)
            entity_id = str(row.get("entity_id", ""))
            if entity_id:
                groups.setdefault(f"{result_atom_id}:{entity_id}", set()).add(record_id)

    for atom_id, atom in ATOMS.items():
        if atom.kind != "conclusion":
            continue
        reference = reference_atoms.get(atom_id, {})
        evidence = (
            set().union(*submitted_result_by_module.values())
            if atom.module == "S" and submitted_result_by_module
            else submitted_result_by_module.get(atom.module, set())
        )
        evidence_groups = (
            {
                key: set().union(*(groups.get(key, set()) for groups in submitted_result_groups_by_module.values()))
                for key in set().union(*(set(groups) for groups in submitted_result_groups_by_module.values()))
            }
            if atom.module == "S" and submitted_result_groups_by_module
            else submitted_result_groups_by_module.get(atom.module, {})
        )
        conclusion_scorer = (
            score_conclusion_hit_atom if reference.get("claim_atoms") else score_conclusion_atom
        )
        scores_by_id[atom_id] = conclusion_scorer(
            atom, submission, reference, evidence, evidence_groups
        )

    scores = [scores_by_id[atom_id] for atom_id in ATOMS]
    warnings = []
    unavailable = [score.atom_id for score in scores if score.status == "unavailable"]
    if unavailable:
        warnings.append(f"private reference is incomplete for {len(unavailable)} atoms: {','.join(unavailable)}")
    unknown_reference_atoms = sorted(set(reference_atoms) - set(ATOMS))
    if unknown_reference_atoms:
        warnings.append(f"private reference contains unknown atoms: {unknown_reference_atoms}")
    return ScoreReport(
        total=float(sum(score.score for score in scores)),
        possible=float(sum(atom.points for atom in ATOMS.values())),
        scorable_possible=float(sum(score.points_possible for score in scores if score.status != "unavailable")),
        atoms=scores,
        warnings=warnings,
    )

