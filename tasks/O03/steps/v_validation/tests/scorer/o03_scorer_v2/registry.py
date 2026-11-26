from __future__ import annotations

from .models import AtomDefinition


_ROWS = [
    ("A-P1", "A", "process", 3.0, "patient-level composition, state and state-excluded endpoint methods"),
    ("A-P2", "A", "process", 3.0, "pathway, TF and communication hypothesis-test methods"),
    ("A-R1", "A", "annotation", 2.0, "A lineage and fibroblast-state annotation"),
    ("A-R2", "A", "result", 3.0, "A primary disease endpoints"),
    ("A-R3", "A", "result", 4.0, "A pathway, TF and communication discoveries"),
    ("A-C1", "A", "conclusion", 2.0, "A scientific boundary conclusions"),
    ("B-P1", "B", "process", 3.0, "B independent patient-level endpoint methods"),
    ("B-P2", "B", "process", 3.0, "B pathway, TF and communication methods"),
    ("B-R1", "B", "annotation", 3.0, "B native annotation"),
    ("B-R2", "B", "result", 3.0, "B independent disease endpoints"),
    ("B-R3", "B", "result", 2.0, "B pathway, TF and communication discoveries"),
    ("B-R4", "B", "result", 2.0, "A objects replicated in B"),
    ("B-C1", "B", "conclusion", 2.0, "A+B joint conclusions"),
    ("C-P1", "C", "process", 3.0, "C PN-AD and sensitivity methods"),
    ("C-P2", "C", "process", 2.0, "C controlled compartment-relation methods"),
    ("C-P3", "C", "process", 2.0, "C pathway, TF and communication methods"),
    ("C-R1", "C", "annotation", 3.0, "C compartment annotation and mural purity"),
    ("C-R2", "C", "result", 4.0, "C A/B endpoint and multicompartment results"),
    ("C-R3", "C", "result", 2.0, "C pathway, TF and communication results"),
    ("C-C1", "C", "conclusion", 2.0, "C ecological and causal-boundary conclusions"),
    ("R-P1", "R", "process", 2.0, "complete independent candidate-ranking method"),
    ("R-P2", "R", "process", 1.0, "non-circular and orthogonal sensitivity methods"),
    ("R-R1", "R", "result", 3.0, "stable and boundary-sensitive response-candidate families"),
    ("R-R2", "R", "result", 2.0, "C response candidates and direct-mechanism observability"),
    ("R-R3", "R", "result", 2.0, "orthogonal response models and mechanism boundary"),
    ("R-C1", "R", "conclusion", 2.0, "candidate-stage conclusions"),
    ("D-P1", "D", "process", 2.0, "time-course statistical method"),
    ("D-P2", "D", "process", 1.0, "robustness and defect-background methods"),
    ("D-R1", "D", "result", 3.0, "stimulus separation"),
    ("D-R2", "D", "result", 2.0, "A/B/C concordance"),
    ("D-C1", "D", "conclusion", 2.0, "D response and causality boundaries"),
    ("E-P1", "E", "process", 2.0, "acquisition identifiability and bounded matrix-association methods"),
    ("E-P2", "E", "process", 2.0, "acquisition-order and identifiability method"),
    ("E-R1", "E", "result", 3.0, "protein-matrix associations, valid negatives and identifiability"),
    ("E-R2", "E", "result", 2.0, "non-identifiable frozen programme directions"),
    ("E-C1", "E", "conclusion", 3.0, "cross-layer identifiability conclusions"),
    ("V-P1", "V", "process", 2.0, "paired programme and feature-family methods"),
    ("V-P2", "V", "process", 1.0, "leave-one-gene and leave-one-patient sensitivity methods"),
    ("V-R1", "V", "result", 3.0, "independent validation results"),
    ("V-C1", "V", "conclusion", 2.0, "V validation boundary conclusions"),
    ("S-R2", "S", "result", 1.0, "cross-stage conflicts, limitations and unresolved questions"),
    ("S-R1", "S", "result", 1.0, "core object continuity"),
    ("S-C1", "S", "conclusion", 3.0, "final scientific chain"),
]

ATOMS = {row[0]: AtomDefinition(*row) for row in _ROWS}


def validate_registry() -> None:
    if len(ATOMS) != 43:
        raise ValueError(f"expected 43 atoms, observed {len(ATOMS)}")
    totals: dict[str, float] = {}
    for atom in ATOMS.values():
        totals[atom.module] = totals.get(atom.module, 0.0) + atom.points
    expected = {"A": 17.0, "B": 18.0, "C": 18.0, "R": 12.0, "D": 10.0, "E": 12.0, "V": 8.0, "S": 5.0}
    if totals != expected:
        raise ValueError(f"module totals differ: {totals}")


validate_registry()

