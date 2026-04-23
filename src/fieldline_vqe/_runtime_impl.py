from __future__ import annotations

from typing import Dict, Tuple

from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from .interfaces import RuntimeBridge

try:
    from qiskit_ibm_runtime import EstimatorOptions, EstimatorV2, QiskitRuntimeService, Session
except Exception:
    EstimatorOptions = None
    EstimatorV2 = None
    QiskitRuntimeService = None
    Session = None

__all__ = ["RuntimeFactory"]


class RuntimeFactory(RuntimeBridge):
    @staticmethod
    def available() -> bool:
        return all(item is not None for item in (EstimatorOptions, EstimatorV2, QiskitRuntimeService, Session))

    @staticmethod
    def require_runtime() -> None:
        if not RuntimeFactory.available():
            raise ImportError("IBM Runtime support requires qiskit-ibm-runtime and configured credentials")

    @staticmethod
    def _identity_layout(isa_circuit: QuantumCircuit):
        return list(range(isa_circuit.num_qubits))

    @staticmethod
    def _resolve_observable_layout(isa_circuit: QuantumCircuit):
        layout = getattr(isa_circuit, "layout", None)
        if layout is None:
            return RuntimeFactory._identity_layout(isa_circuit)
        if hasattr(layout, "final_index_layout"):
            try:
                resolved = layout.final_index_layout()
                if resolved is not None:
                    return resolved
            except Exception:
                pass
        if hasattr(layout, "final_layout") and getattr(layout, "final_layout") is not None:
            return getattr(layout, "final_layout")
        if hasattr(layout, "initial_layout") and getattr(layout, "initial_layout") is not None:
            return getattr(layout, "initial_layout")
        return layout

    @staticmethod
    def layout_diagnostics(isa_circuit: QuantumCircuit) -> Dict[str, object]:
        layout = getattr(isa_circuit, "layout", None)
        if layout is None:
            identity = RuntimeFactory._identity_layout(isa_circuit)
            return {
                "resolved_layout_type": "identity",
                "initial_layout": list(identity),
                "final_index_layout": list(identity),
                "final_layout_present": False,
                "resolved_from_final_index_layout": False,
            }
        resolved = RuntimeFactory._resolve_observable_layout(isa_circuit)
        final_index_layout = None
        if hasattr(layout, "final_index_layout"):
            try:
                final_index_layout = list(layout.final_index_layout())
            except Exception:
                final_index_layout = None
        initial_layout = None
        raw_initial = getattr(layout, "initial_layout", None)
        if raw_initial is not None:
            try:
                initial_layout = [int(raw_initial[pos]._index) for pos in range(len(raw_initial.get_physical_bits()))]
            except Exception:
                initial_layout = None
        return {
            "resolved_layout_type": type(resolved).__name__,
            "initial_layout": initial_layout,
            "final_index_layout": final_index_layout,
            "final_layout_present": getattr(layout, "final_layout", None) is not None,
            "resolved_from_final_index_layout": final_index_layout is not None,
        }

    @staticmethod
    def apply_observable_layout(observables: Dict[str, SparsePauliOp], isa_circuit: QuantumCircuit) -> Tuple[Dict[str, SparsePauliOp], Dict[str, object]]:
        observable_layout = RuntimeFactory._resolve_observable_layout(isa_circuit)
        diagnostics = RuntimeFactory.layout_diagnostics(isa_circuit)
        return {
            name: obs.apply_layout(observable_layout, num_qubits=isa_circuit.num_qubits)
            for name, obs in observables.items()
        }, diagnostics

    @staticmethod
    def transpile_to_isa(circuit: QuantumCircuit, observables: Dict[str, SparsePauliOp], backend, optimization_level: int = 3, seed_transpiler: int = 42) -> Tuple[QuantumCircuit, Dict[str, SparsePauliOp], Dict[str, object]]:
        pm = generate_preset_pass_manager(optimization_level=optimization_level, backend=backend, seed_transpiler=seed_transpiler)
        isa_circuit = pm.run(circuit)
        isa_observables, layout_metadata = RuntimeFactory.apply_observable_layout(observables, isa_circuit)
        return isa_circuit, isa_observables, layout_metadata

    @staticmethod
    def estimator_options(default_shots: int = 10000, resilience_level: int = 0, enable_dd: bool = False, enable_measure_mitigation: bool = False, enable_gate_twirling: bool = False, enable_zne: bool = False):
        RuntimeFactory.require_runtime()
        options = EstimatorOptions()
        options.default_shots = default_shots
        options.resilience_level = resilience_level
        if enable_dd:
            options.dynamical_decoupling.enable = True
            options.dynamical_decoupling.sequence_type = "XpXm"
        if enable_measure_mitigation:
            options.resilience.measure_mitigation = True
        if enable_gate_twirling:
            options.twirling.enable_gates = True
            options.twirling.num_randomizations = "auto"
        if enable_zne:
            options.resilience.zne_mitigation = True
            options.resilience.zne.noise_factors = (1, 3, 5)
            options.resilience.zne.extrapolator = ("exponential", "linear")
        return options
