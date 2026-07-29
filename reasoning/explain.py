from owlready2 import *
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ontology"))
import populate_individuals as pop

onto = pop.onto
bo = pop.bo


def explain_serotonin_syndrome(patient):
    maois = [d for d in patient.takesMedication if bo.MAOI in d.is_a]
    ssris = [d for d in patient.takesMedication if bo.SSRI in d.is_a]
    if maois and ssris:
        return (f"{patient.name} is at Serotonin Syndrome risk because they take "
                f"{maois[0].name} (class: MAOI) and {ssris[0].name} (class: SSRI). "
                f"Rule: MAOI + SSRI co-administration is flagged by definition "
                f"(SerotoninSyndromeRiskPatient ≡ Patient ⊓ ∃takesMedication.MAOI ⊓ ∃takesMedication.SSRI).")
    return None


def explain_bleeding_risk(patient):
    anticoags = [d for d in patient.takesMedication if bo.Anticoagulant in d.is_a]
    nsaids_or_antiplatelets = [d for d in patient.takesMedication
                                if bo.NSAID in d.is_a or bo.Antiplatelet in d.is_a]
    if anticoags and nsaids_or_antiplatelets:
        return (f"{patient.name} is at Bleeding risk because they take "
                f"{anticoags[0].name} (class: Anticoagulant) alongside "
                f"{nsaids_or_antiplatelets[0].name} (class: NSAID/Antiplatelet). "
                f"Rule: Anticoagulant + (NSAID ∪ Antiplatelet) potentiates bleeding.")
    return None


def explain_cyp3a4_toxicity(patient):
    inhibitors = [d for d in patient.takesMedication if bo.CYP3A4Inhibitor in d.is_a]
    substrates = [d for d in patient.takesMedication if bo.CYP3A4Substrate in d.is_a]
    for inhibitor in inhibitors:
        for substrate in substrates:
            shared_enzymes = set(inhibitor.inhibits) & set(substrate.metabolizedBy)
            if shared_enzymes:
                enzyme = list(shared_enzymes)[0]
                return (f"{patient.name} is at CYP3A4 Toxicity risk because "
                        f"{inhibitor.name} inhibits {enzyme.name}, which is the same "
                        f"enzyme that metabolizes {substrate.name}. "
                        f"Rule (SWRL): shared-enzyme inhibition raises substrate blood levels.")
    return None


EXPLAINERS = {
    "SerotoninSyndromeRiskPatient": explain_serotonin_syndrome,
    "BleedingRiskPatient": explain_bleeding_risk,
    "CYP3A4ToxicityRiskPatient": explain_cyp3a4_toxicity,
}


def explain_patient(patient):
    inferred_classes = [c.name for c in patient.is_a if c.name != "Patient"]
    if not inferred_classes:
        return f"{patient.name}: no risk classes inferred — regimen appears safe under current axioms."

    explanations = []
    for cls_name in inferred_classes:
        explainer = EXPLAINERS.get(cls_name)
        if explainer:
            result = explainer(patient)
            if result:
                explanations.append(result)
        else:
            explanations.append(f"{patient.name} classified as {cls_name} (explainer not yet implemented).")
    return "\n".join(explanations)


if __name__ == "__main__":
    try:
        with onto:
            sync_reasoner(infer_property_values=True)
    except OwlReadyInconsistentOntologyError:
        print("❌ Ontology is currently INCONSISTENT (likely P4: pregnant + Warfarin).")
        print("Comment out P4 in populate_individuals.py to see explanations for the other patients.\n")
        sys.exit(1)

    for patient in [pop.P1, pop.P2, pop.P3, pop.P5]:
        print(explain_patient(patient))
        print()