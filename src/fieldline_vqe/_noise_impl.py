from __future__ import annotations

from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error, thermal_relaxation_error

from .config import NoiseDeck
from .constants import ONE_QUBIT_NOISE_GATES, TWO_QUBIT_NOISE_GATES
from .interfaces import NoiseModelFactory

__all__ = ["NoiseFactory", "ONE_QUBIT_NOISE_GATES", "TWO_QUBIT_NOISE_GATES"]


class NoiseFactory(NoiseModelFactory):
    @staticmethod
    def build(cfg: NoiseDeck) -> NoiseModel:
        cfg.validate()
        noise_model = NoiseModel()
        setattr(noise_model, "_reported_gate_error", cfg.gate_error)
        setattr(noise_model, "_reported_two_qubit_gate_error", cfg.effective_two_qubit_gate_error())
        one_qubit = depolarizing_error(cfg.gate_error, 1).compose(thermal_relaxation_error(cfg.t1, cfg.t2, cfg.gate_time))
        noise_model.add_all_qubit_quantum_error(one_qubit, list(ONE_QUBIT_NOISE_GATES))
        two_qubit_relax = thermal_relaxation_error(cfg.t1, cfg.t2, cfg.gate_time).tensor(thermal_relaxation_error(cfg.t1, cfg.t2, cfg.gate_time))
        two_qubit = depolarizing_error(cfg.effective_two_qubit_gate_error(), 2).compose(two_qubit_relax)
        noise_model.add_all_qubit_quantum_error(two_qubit, list(TWO_QUBIT_NOISE_GATES))
        p01, p10 = cfg.readout_pair()
        if p01 > 0 or p10 > 0:
            noise_model.add_all_qubit_readout_error(ReadoutError([[1 - p01, p01], [p10, 1 - p10]]))
        return noise_model
