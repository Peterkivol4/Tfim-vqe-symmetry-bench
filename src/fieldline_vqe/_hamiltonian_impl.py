from __future__ import annotations

from typing import List

import numpy as np
from qiskit.quantum_info import SparsePauliOp

from .constants import DEFAULT_COUPLING
from .interfaces import HamiltonianFactory

__all__ = ["SpinChainBuilder"]


class SpinChainBuilder(HamiltonianFactory):
    @staticmethod
    def ising_chain(n_qubits: int, coupling: float = DEFAULT_COUPLING, field_strength: float = 0.5, periodic: bool = False) -> SparsePauliOp:
        pauli_terms: List[str] = []
        coefficients: List[float] = []
        zz_pairs = [(idx, idx + 1) for idx in range(n_qubits - 1)]
        if periodic and n_qubits > 2:
            zz_pairs.append((n_qubits - 1, 0))
        for left, right in zz_pairs:
            coeff = -float(coupling)
            if coeff != 0.0:
                label = ["I"] * n_qubits
                label[left] = "Z"
                label[right] = "Z"
                pauli_terms.append("".join(reversed(label)))
                coefficients.append(coeff)
        for idx in range(n_qubits):
            coeff = -float(field_strength)
            if coeff != 0.0:
                label = ["I"] * n_qubits
                label[idx] = "X"
                pauli_terms.append("".join(reversed(label)))
                coefficients.append(coeff)
        return SparsePauliOp(pauli_terms, coeffs=np.asarray(coefficients, dtype=float))
