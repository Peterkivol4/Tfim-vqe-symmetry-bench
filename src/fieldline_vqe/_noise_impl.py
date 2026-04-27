from __future__ import annotations

from qiskit.circuit.library import RXGate, RZGate, RZZGate
from qiskit.quantum_info import Operator
from qiskit_aer.noise import (
    NoiseModel,
    ReadoutError,
    amplitude_damping_error,
    coherent_unitary_error,
    depolarizing_error,
    phase_damping_error,
    thermal_relaxation_error,
)

from .config import NoiseBodyConfig, NoiseDeck
from .constants import ONE_QUBIT_NOISE_GATES, TWO_QUBIT_NOISE_GATES
from .interfaces import NoiseModelFactory

__all__ = ["NoiseFactory", "ONE_QUBIT_NOISE_GATES", "TWO_QUBIT_NOISE_GATES"]


class NoiseFactory(NoiseModelFactory):
    @staticmethod
    def build(cfg: NoiseDeck | NoiseBodyConfig) -> NoiseModel:
        cfg.validate()
        noise_model = NoiseModel()
        setattr(noise_model, "_reported_gate_error", cfg.gate_error)
        setattr(noise_model, "_reported_two_qubit_gate_error", cfg.effective_two_qubit_gate_error())
        if isinstance(cfg, NoiseDeck):
            one_qubit = depolarizing_error(cfg.gate_error, 1).compose(thermal_relaxation_error(cfg.t1, cfg.t2, cfg.gate_time))
            noise_model.add_all_qubit_quantum_error(one_qubit, list(ONE_QUBIT_NOISE_GATES))
            two_qubit_relax = thermal_relaxation_error(cfg.t1, cfg.t2, cfg.gate_time).tensor(thermal_relaxation_error(cfg.t1, cfg.t2, cfg.gate_time))
            two_qubit = depolarizing_error(cfg.effective_two_qubit_gate_error(), 2).compose(two_qubit_relax)
            noise_model.add_all_qubit_quantum_error(two_qubit, list(TWO_QUBIT_NOISE_GATES))
        else:
            body = cfg.body
            if body == "local_dephasing":
                one_qubit = phase_damping_error(cfg.strength)
                noise_model.add_all_qubit_quantum_error(one_qubit, list(ONE_QUBIT_NOISE_GATES))
                noise_model.add_all_qubit_quantum_error(one_qubit.tensor(one_qubit), list(TWO_QUBIT_NOISE_GATES))
            elif body == "amplitude_damping":
                one_qubit = amplitude_damping_error(cfg.strength)
                noise_model.add_all_qubit_quantum_error(one_qubit, list(ONE_QUBIT_NOISE_GATES))
                noise_model.add_all_qubit_quantum_error(one_qubit.tensor(one_qubit), list(TWO_QUBIT_NOISE_GATES))
            elif body in {"depolarizing", "hardware"}:
                one_qubit = depolarizing_error(cfg.gate_error, 1)
                two_qubit = depolarizing_error(cfg.effective_two_qubit_gate_error(), 2)
                if body == "hardware":
                    one_qubit = one_qubit.compose(thermal_relaxation_error(cfg.t1, cfg.t2, cfg.gate_time))
                    two_qubit_relax = thermal_relaxation_error(cfg.t1, cfg.t2, cfg.gate_time).tensor(thermal_relaxation_error(cfg.t1, cfg.t2, cfg.gate_time))
                    two_qubit = two_qubit.compose(two_qubit_relax)
                noise_model.add_all_qubit_quantum_error(one_qubit, list(ONE_QUBIT_NOISE_GATES))
                noise_model.add_all_qubit_quantum_error(two_qubit, list(TWO_QUBIT_NOISE_GATES))
            elif body == "correlated_zz_noise":
                theta = cfg.effective_coherence_angle()
                two_qubit = coherent_unitary_error(Operator(RZZGate(2.0 * theta)))
                noise_model.add_all_qubit_quantum_error(two_qubit, list(TWO_QUBIT_NOISE_GATES))
            elif body == "coherent_x_drift":
                one_qubit = coherent_unitary_error(Operator(RXGate(cfg.effective_coherence_angle())))
                noise_model.add_all_qubit_quantum_error(one_qubit, list(ONE_QUBIT_NOISE_GATES))
            elif body == "coherent_z_drift":
                one_qubit = coherent_unitary_error(Operator(RZGate(cfg.effective_coherence_angle())))
                noise_model.add_all_qubit_quantum_error(one_qubit, list(ONE_QUBIT_NOISE_GATES))
            elif body in {"ideal", "readout_only"}:
                pass
            else:  # pragma: no cover - guarded by config validation
                raise ValueError(f"Unsupported noise body: {body}")
        p01, p10 = cfg.readout_pair()
        if p01 > 0 or p10 > 0:
            noise_model.add_all_qubit_readout_error(ReadoutError([[1 - p01, p01], [p10, 1 - p10]]))
        return noise_model
