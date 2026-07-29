import sys
import os
import pytest
from owlready2 import *

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ontology"))


@pytest.fixture
def fresh_onto():
    """Reload a clean ontology + individuals for each test, avoiding state leakage."""
    for mod_name in list(sys.modules):
        if mod_name in ("build_ontology", "populate_individuals", "populate_bad_case"):
            del sys.modules[mod_name]
    default_world.ontologies.clear()

    import populate_individuals as pop
    with pop.onto:
        sync_reasoner(infer_property_values=True)
    return pop


EXPECTED_CLASSES = {
    "P1_SerotoninRisk": "SerotoninSyndromeRiskPatient",
    "P2_CYP3A4Risk": "CYP3A4ToxicityRiskPatient",
    "P3_BleedingRisk": "BleedingRiskPatient",
}


def test_serotonin_syndrome_risk_detected(fresh_onto):
    p1 = fresh_onto.P1
    class_names = [c.name for c in p1.is_a]
    assert "SerotoninSyndromeRiskPatient" in class_names


def test_cyp3a4_toxicity_risk_detected(fresh_onto):
    p2 = fresh_onto.P2
    class_names = [c.name for c in p2.is_a]
    assert "CYP3A4ToxicityRiskPatient" in class_names


def test_bleeding_risk_detected(fresh_onto):
    p3 = fresh_onto.P3
    class_names = [c.name for c in p3.is_a]
    assert "BleedingRiskPatient" in class_names


def test_safe_patient_has_no_risk_classes(fresh_onto):
    p5 = fresh_onto.P5
    risk_classes = [c.name for c in p5.is_a if c.name != "Patient"]
    assert risk_classes == []


def test_pregnancy_contraindication_causes_inconsistency():
    for mod_name in list(sys.modules):
        if mod_name in ("build_ontology", "populate_individuals", "populate_bad_case"):
            del sys.modules[mod_name]
    default_world.ontologies.clear()

    import populate_bad_case as bad

    with pytest.raises(OwlReadyInconsistentOntologyError):
        with bad.onto:
            sync_reasoner(infer_property_values=True)