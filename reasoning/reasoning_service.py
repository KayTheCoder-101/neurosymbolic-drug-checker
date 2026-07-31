"""
Singleton reasoning service. Loads the ontology once, exposes a thread-safe
interface for checking arbitrary drug combinations without permanently
polluting the ontology with temporary/demo data.
"""

import sys
import os
import threading
import uuid
from owlready2 import sync_reasoner, destroy_entity, OwlReadyInconsistentOntologyError

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ontology"))


class ReasoningService:
    def __init__(self):
        self._lock = threading.Lock()
        import populate_individuals as pop
        from explain import explain_patient

        self.pop = pop
        self.bo = pop.bo
        self.onto = pop.onto
        self._explain_patient = explain_patient
        self._sync()

    def _sync(self):
        with self.onto:
            sync_reasoner(infer_property_values=True)

    def get_drug_by_name(self, name: str):
        """Case-insensitive lookup by individual name."""
        for drug in self.onto.search(type=self.bo.Drug):
            if drug.name.lower() == name.lower():
                return drug
        return None

    def list_known_drugs(self) -> list[str]:
        return sorted(d.name for d in self.onto.search(type=self.bo.Drug))

    def check_static_patient(self, patient_short_id: str) -> dict:
        """For the pre-baked P1-P5 demo patients."""
        with self._lock:
            patient = getattr(self.pop, patient_short_id, None)
            if patient is None:
                return {"error": f"Unknown patient ID: {patient_short_id}"}
            inferred = [c.name for c in patient.is_a if c.name != "Patient"]
            explain_result = self._explain_patient(patient)
            return {
                "inferred_classes": inferred,
                "explanation": explain_result["explanation"],
                "severity": explain_result["severity"],
            }

    def check_custom_regimen(self, drug_names: list[str], pregnant: bool = False) -> dict:
        with self._lock:
            unknown = [name for name in drug_names if self.get_drug_by_name(name) is None]
            if unknown:
                return {"error": f"Unknown drug(s): {', '.join(unknown)}",
                         "known_drugs": self.list_known_drugs()}

            temp_name = f"TempPatient_{uuid.uuid4().hex[:8]}"
            with self.onto:
                if pregnant:
                    patient = self.bo.PregnantPatient(temp_name)
                    patient.isPregnant = [True]
                else:
                    patient = self.bo.Patient(temp_name)
                patient.takesMedication = [self.get_drug_by_name(n) for n in drug_names]

            try:
                self._sync()
                inferred = [c.name for c in patient.is_a if c.name != "Patient"]
                explain_result = self._explain_patient(patient)
                result = {
                    "inferred_classes": inferred,
                    "explanation": explain_result["explanation"],
                    "severity": explain_result["severity"],
                    "consistent": True,
                }
            except OwlReadyInconsistentOntologyError:
                result = {"inferred_classes": [], "explanation": None,
                          "severity": "Contraindicated",
                          "consistent": False,
                          "message": "This combination creates a logically impossible "
                                     "state under the ontology's axioms (e.g. an absolute "
                                     "contraindication)."}
            finally:
                destroy_entity(patient)
                try:
                    self._sync()
                except OwlReadyInconsistentOntologyError:
                    pass

            return result


_service_instance = None


def get_reasoning_service() -> ReasoningService:
    global _service_instance
    if _service_instance is None:
        _service_instance = ReasoningService()
    return _service_instance

if __name__ == "__main__":
    service = get_reasoning_service()
    print("Known drugs:", service.list_known_drugs())
    print()
    print("Static P1:", service.check_static_patient("P1"))
    print()
    print("Custom (Phenelzine + Sertraline):", service.check_custom_regimen(["Phenelzine", "Sertraline"]))
    print()
    print("Custom (Diazepam only):", service.check_custom_regimen(["Diazepam"]))