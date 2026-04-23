from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter

from .constants import VALID_ANSATZES
from .interfaces import AnsatzFactory

__all__ = ["CircuitFactory", "VALID_ANSATZES"]


class CircuitFactory(AnsatzFactory):
    @staticmethod
    def build(name: str, n_qubits: int, depth: int) -> QuantumCircuit:
        key = name.lower()
        if key == "hardware_efficient":
            return CircuitFactory.hardware_efficient(n_qubits, depth)
        if key == "symmetry_preserving":
            return CircuitFactory.symmetry_preserving_tfim(n_qubits, depth)
        if key == "problem_inspired":
            return CircuitFactory.problem_inspired_tfim(n_qubits, depth)
        raise ValueError("unsupported ansatz")

    @staticmethod
    def hardware_efficient(n_qubits: int, depth: int) -> QuantumCircuit:
        circuit = QuantumCircuit(n_qubits, name=f"he_depth_{depth}")
        for layer in range(depth):
            for qubit in range(n_qubits):
                circuit.ry(Parameter(f"theta_{layer}_{qubit}"), qubit)
                circuit.rz(Parameter(f"phi_{layer}_{qubit}"), qubit)
            for qubit in range(n_qubits - 1):
                circuit.cx(qubit, qubit + 1)
        for qubit in range(n_qubits):
            circuit.ry(Parameter(f"theta_final_{qubit}"), qubit)
            circuit.rz(Parameter(f"phi_final_{qubit}"), qubit)
        return circuit

    @staticmethod
    def symmetry_preserving_tfim(n_qubits: int, depth: int) -> QuantumCircuit:
        circuit = QuantumCircuit(n_qubits, name=f"symm_tfim_depth_{depth}")
        circuit.h(range(n_qubits))
        for layer in range(depth):
            for qubit in range(n_qubits - 1):
                circuit.rzz(Parameter(f"zz_{layer}_{qubit}"), qubit, qubit + 1)
            for qubit in range(n_qubits):
                circuit.rx(Parameter(f"x_{layer}_{qubit}"), qubit)
        return circuit

    @staticmethod
    def problem_inspired_tfim(n_qubits: int, depth: int) -> QuantumCircuit:
        circuit = QuantumCircuit(n_qubits, name=f"pi_tfim_depth_{depth}")
        circuit.h(range(n_qubits))
        for layer in range(depth):
            for start in (0, 1):
                for qubit in range(start, n_qubits - 1, 2):
                    circuit.rzz(Parameter(f"brickzz_{layer}_{start}_{qubit}"), qubit, qubit + 1)
            for qubit in range(n_qubits):
                circuit.rx(Parameter(f"mixx_{layer}_{qubit}"), qubit)
            for qubit in range(n_qubits - 1):
                circuit.rxx(Parameter(f"corrx_{layer}_{qubit}"), qubit, qubit + 1)
        return circuit
