from owlready2 import *
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ontology"))
import populate_individuals as pop

onto = pop.onto

try:
    with onto:
        sync_reasoner(infer_property_values=True)
    print("✅ Ontology is CONSISTENT.\n")

    print("--- Inferred class memberships ---")
    for patient in [pop.P1, pop.P2, pop.P3, pop.P5]:
        classes = [c.name for c in patient.is_a if c.name != "Patient"]
        print(f"{patient.name}: {classes}")

except OwlReadyInconsistentOntologyError:
    print("❌ ONTOLOGY IS INCONSISTENT.")
    print("This is expected if P4 (pregnant + Warfarin) was asserted —")
    print("the reasoner has detected a logically impossible combination.")