from owlready2 import *
import os
import populate_individuals as pop

onto = pop.onto
bo = pop.bo

with onto:
    P4 = bo.PregnantPatient("P4_PregnancyContradiction")
    P4.isPregnant = [True]
    P4.takesMedication = [pop.Warfarin]

script_dir = os.path.dirname(os.path.abspath(__file__))
onto.save(file=os.path.join(script_dir, "drugkr_bad_case.owl"), format="rdfxml")
print("Bad-case ontology saved separately as drugkr_bad_case.owl")