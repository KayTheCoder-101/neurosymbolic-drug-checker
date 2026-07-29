from owlready2 import *
import os

onto = get_ontology("http://example.org/drugkr.owl")
with onto:
    class Drug(Thing): pass
    class Patient(Thing): pass
    class Enzyme(Thing): pass
    class MedicalCondition(Thing): pass
    class MAOI(Drug): pass
    class SSRI(Drug): pass
    class Triptan(Drug): pass
    class Opioid(Drug): pass
    class Benzodiazepine(Drug): pass
    class Anticoagulant(Drug): pass
    class Antiplatelet(Drug): pass
    class NSAID(Drug): pass
    class CYP3A4Inhibitor(Drug): pass
    class CYP3A4Substrate(Drug): pass
    class QTProlongingAgent(Drug): pass
    class Sympathomimetic(Drug): pass
    class InteractionMechanism(Thing): pass
    class SeverityLevel(Thing): pass

    class takesMedication(ObjectProperty):
        domain = [Patient]
        range = [Drug]

    class hasCondition(ObjectProperty):
        domain = [Patient]
        range = [MedicalCondition]

    class metabolizedBy(ObjectProperty):
        domain = [Drug]
        range = [Enzyme]

    class inhibits(ObjectProperty):
        domain = [Drug]
        range = [Enzyme]

    class hasMechanism(ObjectProperty):
        domain = [Patient]
        range = [InteractionMechanism]

    class hasSeverity(ObjectProperty):
        domain = [InteractionMechanism]
        range = [SeverityLevel]

    class standardDoseMg(Drug >> float): pass
    class halfLifeHours(Drug >> float): pass
    class ageYears(Patient >> int): pass
    class isPregnant(Patient >> bool): pass
    class creatinineClearance(Patient >> float): pass

    class SerotoninSyndromeRiskPatient(Patient):
        equivalent_to = [
            Patient
            & (takesMedication.some(MAOI))
            & (takesMedication.some(SSRI))
        ]

    class HypertensiveCrisisRiskPatient(Patient):
        equivalent_to = [
            Patient
            & (takesMedication.some(MAOI))
            & (takesMedication.some(Sympathomimetic))
        ]

    class BleedingRiskPatient(Patient):
        equivalent_to = [
            Patient
            & (
                (takesMedication.some(NSAID))
                | (takesMedication.some(Antiplatelet))
              )
            & (takesMedication.some(Anticoagulant))
        ]

    class QTProlongationRiskPatient(Patient):
        equivalent_to = [
            Patient
            & (takesMedication.min(2, QTProlongingAgent))
        ]

    class CNSDepressionRiskPatient(Patient):
        equivalent_to = [
            Patient
            & (takesMedication.some(Opioid))
            & (takesMedication.some(Benzodiazepine))
        ]

    class CYP3A4ToxicityRiskPatient(Patient):
        pass  # populated via SWRL rule below, not equivalent_to

    cyp3a4_rule = Imp()
    cyp3a4_rule.set_as_rule("""
        Patient(?p), takesMedication(?p, ?d1), CYP3A4Inhibitor(?d1), inhibits(?d1, ?e),
        takesMedication(?p, ?d2), CYP3A4Substrate(?d2), metabolizedBy(?d2, ?e)
        -> CYP3A4ToxicityRiskPatient(?p)
    """)

    class PregnantPatient(Patient): pass

    class AbsoluteContraindicationInPregnancy(Drug): pass

    class ForbiddenPregnancyRegimen(Thing):
        equivalent_to = [
            Nothing,
            PregnantPatient
            & (takesMedication.some(AbsoluteContraindicationInPregnancy))
        ]

script_dir = os.path.dirname(os.path.abspath(__file__))
onto.save(file=os.path.join(script_dir, "drugkr.owl"), format="rdfxml")
print("Ontology saved successfully.")
print(f"Classes: {len(list(onto.classes()))}")
print(f"Object properties: {len(list(onto.object_properties()))}")
print(f"Data properties: {len(list(onto.data_properties()))}")