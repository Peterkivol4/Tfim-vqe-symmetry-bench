from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Protocol

from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp

from .config import BehaviorConfig, NoiseDeck, RunSpec, StudySpec
from .results import TrialRecord


class AnsatzFactory(ABC):
    @staticmethod
    @abstractmethod
    def build(name: str, n_qubits: int, depth: int) -> QuantumCircuit:
        raise NotImplementedError


class HamiltonianFactory(ABC):
    @staticmethod
    @abstractmethod
    def ising_chain(n_qubits: int, coupling: float = 1.0, field_strength: float = 0.5, periodic: bool = False) -> SparsePauliOp:
        raise NotImplementedError


class NoiseModelFactory(ABC):
    @staticmethod
    @abstractmethod
    def build(cfg: NoiseDeck):
        raise NotImplementedError


class RuntimeBridge(ABC):
    @staticmethod
    @abstractmethod
    def transpile_to_isa(circuit: QuantumCircuit, observables: Dict[str, SparsePauliOp], backend, optimization_level: int = 3, seed_transpiler: int = 42):
        raise NotImplementedError


class RecordAssembler(ABC):
    @staticmethod
    @abstractmethod
    def build_trial_record(**kwargs) -> TrialRecord:
        raise NotImplementedError


class ExperimentService(ABC):
    @abstractmethod
    def run_vqe(self, *args, **kwargs) -> TrialRecord:
        raise NotImplementedError

    @abstractmethod
    def save_summary(self, *args, **kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_plot(self, *args, **kwargs) -> None:
        raise NotImplementedError


class BehaviorService(ABC):
    @staticmethod
    @abstractmethod
    def build(rows, aggregate, crossover, coupling: float, config: BehaviorConfig):
        raise NotImplementedError


class StudyService(ABC):
    @staticmethod
    @abstractmethod
    def run(spec: StudySpec, noise_template: NoiseDeck):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def save(prefix, spec: StudySpec, payload):
        raise NotImplementedError


class PipelineRunner(Protocol):
    def __call__(self, spec: RunSpec | StudySpec, noise: NoiseDeck):
        ...


__all__ = [
    "AnsatzFactory", "HamiltonianFactory", "NoiseModelFactory", "RuntimeBridge", "RecordAssembler", "ExperimentService",
    "BehaviorService", "StudyService", "PipelineRunner",
]
