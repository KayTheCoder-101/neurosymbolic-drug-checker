from owlready2 import *
import build_ontology as bo

onto = bo.onto

with onto:
    # ---------------- Enzyme ----------------
    CYP3A4 = bo.Enzyme("CYP3A4")

    # ---------------- Drugs ----------------
    # Single-category drugs
    Phenelzine        = bo.MAOI("Phenelzine")
    Tranylcypromine    = bo.MAOI("Tranylcypromine")
    Sertraline         = bo.SSRI("Sertraline")
    Fluoxetine         = bo.SSRI("Fluoxetine")
    Sumatriptan        = bo.Triptan("Sumatriptan")
    Tramadol           = bo.Opioid("Tramadol")
    Morphine           = bo.Opioid("Morphine")
    Diazepam           = bo.Benzodiazepine("Diazepam")
    Clopidogrel        = bo.Antiplatelet("Clopidogrel")
    Ibuprofen          = bo.NSAID("Ibuprofen")
    Ketoconazole       = bo.CYP3A4Inhibitor("Ketoconazole")
    Clarithromycin     = bo.CYP3A4Inhibitor("Clarithromycin")
    Simvastatin        = bo.CYP3A4Substrate("Simvastatin")
    Haloperidol        = bo.QTProlongingAgent("Haloperidol")
    Pseudoephedrine    = bo.Sympathomimetic("Pseudoephedrine")

    # Multi-category drugs — create with primary class, then append the rest
    Citalopram = bo.SSRI("Citalopram")
    Citalopram.is_a.append(bo.QTProlongingAgent)

    Alprazolam = bo.Benzodiazepine("Alprazolam")
    Alprazolam.is_a.append(bo.CYP3A4Substrate)

    Aspirin = bo.NSAID("Aspirin")
    Aspirin.is_a.append(bo.Antiplatelet)

    Amiodarone = bo.QTProlongingAgent("Amiodarone")
    Amiodarone.is_a.append(bo.CYP3A4Inhibitor)

    Warfarin = bo.Anticoagulant("Warfarin")
    Warfarin.is_a.append(bo.AbsoluteContraindicationInPregnancy)

    # ---------------- Enzyme relationships (for the CYP3A4 SWRL rule) ----------------
    Alprazolam.metabolizedBy = [CYP3A4]
    Simvastatin.metabolizedBy = [CYP3A4]
    Ketoconazole.inhibits = [CYP3A4]
    Clarithromycin.inhibits = [CYP3A4]
    Amiodarone.inhibits = [CYP3A4]

    # ---------------- Sample patients ----------------

    # P1: should trigger SerotoninSyndromeRiskPatient
    P1 = bo.Patient("P1_SerotoninRisk")
    P1.takesMedication = [Phenelzine, Sertraline]

    # P2: should trigger CYP3A4ToxicityRiskPatient (via SWRL, same enzyme)
    P2 = bo.Patient("P2_CYP3A4Risk")
    P2.takesMedication = [Ketoconazole, Simvastatin]

    # P3: should trigger BleedingRiskPatient
    P3 = bo.Patient("P3_BleedingRisk")
    P3.takesMedication = [Warfarin, Aspirin]

    # P4: DELIBERATELY DANGEROUS — pregnant + absolute contraindication
    # this should make the whole ontology INCONSISTENT
    P4 = bo.PregnantPatient("P4_PregnancyContradiction")
    P4.isPregnant = [True]
    P4.takesMedication = [Warfarin]

    # P5: safe baseline patient — should NOT trigger any risk class
    P5 = bo.Patient("P5_Safe")
    P5.takesMedication = [Diazepam]

onto.save(file="ontology/drugkr.owl", format="rdfxml")
print("Individuals populated and saved.")
print(f"Total individuals: {len(list(onto.individuals()))}")
