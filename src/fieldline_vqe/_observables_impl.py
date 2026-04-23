from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import DensityMatrix, SparsePauliOp, Statevector, entropy, partial_trace, state_fidelity

StateLike = Statevector | DensityMatrix
Distribution = Mapping[str, float]

__all__ = ["ObservableBundle", "MeasurementTerm", "MeasurementGroup", "ObservableFactory", "MeasurementPlanner", "StateAnalyzer", "expectation", "energy_variance", "observable_error_l2"]


@dataclass
class ObservableBundle:
    primary: Dict[str, SparsePauliOp]
    correlation_profiles: Dict[str, list[tuple[str, SparsePauliOp]]]


@dataclass
class MeasurementTerm:
    name: str
    label: str
    coeff: float


@dataclass
class MeasurementGroup:
    basis: str
    terms: List[MeasurementTerm]

    @property
    def coefficient_weight(self) -> float:
        return float(sum(abs(term.coeff) for term in self.terms))


class ObservableFactory:
    @staticmethod
    def zero_operator(n_qubits: int) -> SparsePauliOp:
        return SparsePauliOp(["I" * n_qubits], coeffs=np.asarray([0.0], dtype=float))

    @staticmethod
    def site(n_qubits: int, axis: str, index: int) -> SparsePauliOp:
        label = ["I"] * n_qubits
        label[index] = axis
        return SparsePauliOp(["".join(reversed(label))], coeffs=np.asarray([1.0], dtype=float))

    @staticmethod
    def magnetization(n_qubits: int, axis: str) -> SparsePauliOp:
        terms, coeffs = [], []
        for idx in range(n_qubits):
            label = ["I"] * n_qubits
            label[idx] = axis
            terms.append("".join(reversed(label)))
            coeffs.append(1.0 / n_qubits)
        return SparsePauliOp(terms, coeffs=np.asarray(coeffs, dtype=float))

    @staticmethod
    def magnetization_profile(n_qubits: int, axis: str) -> list[tuple[str, SparsePauliOp]]:
        return [(f"{axis}_{idx}", ObservableFactory.site(n_qubits, axis, idx)) for idx in range(n_qubits)]

    @staticmethod
    def mean_nn_correlation(n_qubits: int, axis: str) -> SparsePauliOp:
        if n_qubits < 2:
            return ObservableFactory.zero_operator(n_qubits)
        terms, coeffs = [], []
        for idx in range(n_qubits - 1):
            label = ["I"] * n_qubits
            label[idx] = axis
            label[idx + 1] = axis
            terms.append("".join(reversed(label)))
            coeffs.append(1.0 / max(1, n_qubits - 1))
        return SparsePauliOp(terms, coeffs=np.asarray(coeffs, dtype=float))

    @staticmethod
    def pair(n_qubits: int, axis: str, left: int, right: int) -> SparsePauliOp:
        label = ["I"] * n_qubits
        label[left] = axis
        label[right] = axis
        return SparsePauliOp(["".join(reversed(label))], coeffs=np.asarray([1.0], dtype=float))

    @staticmethod
    def global_x_parity(n_qubits: int) -> SparsePauliOp:
        return SparsePauliOp(["X" * n_qubits], coeffs=np.asarray([1.0], dtype=float))

    @staticmethod
    def projector_x_parity(n_qubits: int, sector: int = 1) -> np.ndarray:
        identity = np.eye(2**n_qubits, dtype=complex)
        parity = ObservableFactory.global_x_parity(n_qubits).to_matrix()
        sign = 1.0 if int(sector) >= 0 else -1.0
        return 0.5 * (identity + sign * parity)

    @staticmethod
    def projector_even_x_parity(n_qubits: int) -> np.ndarray:
        return ObservableFactory.projector_x_parity(n_qubits, sector=1)

    @staticmethod
    def default_bundle(n_qubits: int) -> ObservableBundle:
        return ObservableBundle(
            primary={
                "magnetization_x": ObservableFactory.magnetization(n_qubits, "X"),
                "magnetization_z": ObservableFactory.magnetization(n_qubits, "Z"),
                "correlation_xx_mean": ObservableFactory.mean_nn_correlation(n_qubits, "X"),
                "correlation_zz_mean": ObservableFactory.mean_nn_correlation(n_qubits, "Z"),
                "x_parity": ObservableFactory.global_x_parity(n_qubits),
            },
            correlation_profiles={
                "magnetization_x_profile": ObservableFactory.magnetization_profile(n_qubits, "X"),
                "magnetization_z_profile": ObservableFactory.magnetization_profile(n_qubits, "Z"),
                "correlation_xx_profile": [(f"XX_{i}_{i+1}", ObservableFactory.pair(n_qubits, "X", i, i + 1)) for i in range(n_qubits - 1)],
                "correlation_zz_profile": [(f"ZZ_{i}_{i+1}", ObservableFactory.pair(n_qubits, "Z", i, i + 1)) for i in range(n_qubits - 1)],
            },
        )


class MeasurementPlanner:
    @staticmethod
    def _qwc_conflict(left: str, right: str) -> bool:
        return not MeasurementPlanner._compatible_with_basis(left, right)

    @staticmethod
    def _largest_first_order(terms: Sequence[MeasurementTerm]) -> List[int]:
        degrees = []
        for idx, term in enumerate(terms):
            degree = sum(
                1
                for jdx, other in enumerate(terms)
                if jdx != idx and MeasurementPlanner._qwc_conflict(term.label, other.label)
            )
            degrees.append((degree, sum(axis != "I" for axis in term.label), idx))
        return [idx for _, _, idx in sorted(degrees, reverse=True)]

    @staticmethod
    def pauli_terms(operator: SparsePauliOp, prefix: str = "term") -> List[MeasurementTerm]:
        labels = operator.paulis.to_labels()
        return [MeasurementTerm(name=f"{prefix}_{idx}", label=label, coeff=float(np.real(coeff))) for idx, (label, coeff) in enumerate(zip(labels, operator.coeffs))]

    @staticmethod
    def _compatible_with_basis(current: str, candidate: str) -> bool:
        for existing, incoming in zip(current, candidate):
            if existing == "I" or incoming == "I":
                continue
            if existing != incoming:
                return False
        return True

    @staticmethod
    def _merge_basis(current: str, candidate: str) -> str:
        return "".join(existing if existing != "I" else incoming for existing, incoming in zip(current, candidate))

    @staticmethod
    def _conflict_graph(terms: Sequence[MeasurementTerm]) -> List[set[int]]:
        graph = [set() for _ in terms]
        for idx, left in enumerate(terms):
            for jdx in range(idx + 1, len(terms)):
                right = terms[jdx]
                if MeasurementPlanner._qwc_conflict(left.label, right.label):
                    graph[idx].add(jdx)
                    graph[jdx].add(idx)
        return graph

    @staticmethod
    def group_qwc(terms: Sequence[MeasurementTerm]) -> List[MeasurementGroup]:
        if not terms:
            return []
        adjacency = MeasurementPlanner._conflict_graph(terms)
        uncolored: set[int] = set(range(len(terms)))
        colors: Dict[int, int] = {}

        def score(node: int) -> tuple[int, int, int, int]:
            neighbor_colors = {colors[nbr] for nbr in adjacency[node] if nbr in colors}
            degree = len(adjacency[node])
            non_identity_weight = sum(axis != "I" for axis in terms[node].label)
            return (len(neighbor_colors), degree, non_identity_weight, -node)

        while uncolored:
            node = max(uncolored, key=score)
            forbidden = {colors[nbr] for nbr in adjacency[node] if nbr in colors}
            color = 0
            while color in forbidden:
                color += 1
            colors[node] = color
            uncolored.remove(node)

        grouped_indices: Dict[int, List[int]] = {}
        for idx, color in colors.items():
            grouped_indices.setdefault(color, []).append(idx)

        groups: List[MeasurementGroup] = []
        for color in sorted(grouped_indices):
            group_terms = [terms[idx] for idx in grouped_indices[color]]
            basis = "I" * len(group_terms[0].label)
            for term in group_terms:
                basis = MeasurementPlanner._merge_basis(basis, term.label)
            groups.append(MeasurementGroup(basis=basis, terms=group_terms))
        return groups

    @staticmethod
    def measurement_circuit(circuit: QuantumCircuit, basis: str) -> QuantumCircuit:
        measured = circuit.copy()
        for logical, axis in enumerate(reversed(basis)):
            if axis == "X":
                measured.h(logical)
            elif axis == "Y":
                measured.sdg(logical)
                measured.h(logical)
        measured.measure_all()
        return measured

    @staticmethod
    def _clean_distribution(distribution: Distribution) -> Dict[str, float]:
        cleaned = {bitstring.replace(" ", ""): float(value) for bitstring, value in distribution.items()}
        total = float(sum(cleaned.values()))
        if total <= 0:
            return {key: 0.0 for key in cleaned}
        return {key: value / total for key, value in cleaned.items()}

    @staticmethod
    def distribution_to_vector(distribution: Distribution, n_qubits: int) -> np.ndarray:
        probs = np.zeros(2**n_qubits, dtype=float)
        for bitstring, value in MeasurementPlanner._clean_distribution(distribution).items():
            probs[int(bitstring, 2)] += float(value)
        return probs

    @staticmethod
    def vector_to_distribution(probabilities: np.ndarray, n_qubits: int) -> Dict[str, float]:
        total = float(np.sum(probabilities))
        if total <= 0:
            probabilities = np.full_like(probabilities, 1.0 / len(probabilities), dtype=float)
        else:
            probabilities = probabilities / total
        return {
            format(index, f"0{n_qubits}b"): float(value)
            for index, value in enumerate(probabilities)
            if abs(float(value)) > 1e-15
        }

    @staticmethod
    def mitigate_readout_distribution(distribution: Distribution, n_qubits: int, p01: float, p10: float) -> Dict[str, float]:
        if p01 <= 0.0 and p10 <= 0.0:
            return MeasurementPlanner._clean_distribution(distribution)
        transfer_1q = np.asarray(
            [[1.0 - p01, p10], [p01, 1.0 - p10]],
            dtype=float,
        )
        transfer = transfer_1q
        for _ in range(n_qubits - 1):
            transfer = np.kron(transfer, transfer_1q)
        observed = MeasurementPlanner.distribution_to_vector(distribution, n_qubits)
        mitigated = np.linalg.pinv(transfer) @ observed
        mitigated = np.clip(np.real_if_close(mitigated, tol=1e8), 0.0, None)
        return MeasurementPlanner.vector_to_distribution(np.asarray(mitigated, dtype=float), n_qubits)

    @staticmethod
    def even_parity_probability(distribution: Distribution) -> float:
        cleaned = MeasurementPlanner._clean_distribution(distribution)
        return float(sum(value for bitstring, value in cleaned.items() if bitstring.count("1") % 2 == 0))

    @staticmethod
    def term_expectation_from_counts(counts: Distribution, label: str) -> float:
        cleaned = MeasurementPlanner._clean_distribution(counts)
        active_positions = [idx for idx, axis in enumerate(label) if axis != "I"]
        expectation_value = 0.0
        for bitstring, probability in cleaned.items():
            eigenvalue = 1.0
            for position in active_positions:
                if bitstring[-1 - position] == "1":
                    eigenvalue *= -1.0
            expectation_value += eigenvalue * probability
        return float(expectation_value)

    @staticmethod
    def group_value_and_variance(counts: Distribution, group: MeasurementGroup) -> tuple[float, float]:
        cleaned = MeasurementPlanner._clean_distribution(counts)
        expectations = {term.name: MeasurementPlanner.term_expectation_from_counts(cleaned, term.label) for term in group.terms}
        value = float(sum(term.coeff * expectations[term.name] for term in group.terms))
        second_moment = 0.0
        for bitstring, probability in cleaned.items():
            shot_value = 0.0
            for term in group.terms:
                eigenvalue = 1.0
                for position, axis in enumerate(term.label):
                    if axis == "I":
                        continue
                    if bitstring[-1 - position] == "1":
                        eigenvalue *= -1.0
                shot_value += term.coeff * eigenvalue
            second_moment += probability * (shot_value**2)
        variance = max(float(second_moment - value**2), 0.0)
        return value, variance

    @staticmethod
    def allocate_shots(groups: Sequence[MeasurementGroup], total_shots: int, strategy: str = "equal", empirical_variances: Dict[str, float] | None = None) -> Dict[str, int]:
        if total_shots <= 0:
            return {group.basis: 0 for group in groups}
        if strategy == "equal":
            weights = {group.basis: 1.0 for group in groups}
        elif strategy == "coefficient_weighted":
            weights = {group.basis: max(group.coefficient_weight, 1e-12) for group in groups}
        elif strategy == "variance_weighted":
            weights = {
                group.basis: max(float(np.sqrt(max((empirical_variances or {}).get(group.basis, group.coefficient_weight), 0.0))), 1e-12)
                for group in groups
            }
        else:
            raise ValueError(f"Unsupported shot-allocation strategy: {strategy}")
        total_weight = sum(weights.values())
        allocation = {basis: max(1, int(round(total_shots * weight / total_weight))) for basis, weight in weights.items()}
        delta = total_shots - sum(allocation.values())
        ordered = list(weights.keys()) or [""]
        index = 0
        while delta != 0 and ordered:
            key = ordered[index % len(ordered)]
            if delta > 0:
                allocation[key] += 1
                delta -= 1
            elif allocation[key] > 1:
                allocation[key] -= 1
                delta += 1
            index += 1
            if index > 10000:
                break
        return allocation

    @staticmethod
    def describe_groups(groups: Sequence[MeasurementGroup]) -> List[Dict[str, object]]:
        return [
            {
                "basis": group.basis,
                "num_terms": len(group.terms),
                "coefficient_weight": group.coefficient_weight,
                "terms": [{"name": term.name, "label": term.label, "coeff": term.coeff} for term in group.terms],
            }
            for group in groups
        ]


def expectation(state: StateLike, observable: SparsePauliOp) -> float:
    return float(np.real(state.expectation_value(observable)))


def energy_variance(state: StateLike, hamiltonian: SparsePauliOp) -> float:
    matrix = np.asarray(hamiltonian.to_matrix(), dtype=complex)
    moment_1 = expectation(state, hamiltonian)
    if isinstance(state, Statevector):
        vec = np.asarray(state.data, dtype=complex)
        hpsi = matrix @ vec
        moment_2 = float(np.real(np.vdot(hpsi, hpsi)))
    elif isinstance(state, DensityMatrix):
        rho = np.asarray(state.data, dtype=complex)
        moment_2 = float(np.real(np.trace(rho @ (matrix @ matrix))))
    else:
        return 0.0
    return float(max(moment_2 - moment_1**2, 0.0))


class StateAnalyzer:
    @staticmethod
    def half_chain_entropy(state: StateLike, n_qubits: int) -> float | None:
        if isinstance(state, Statevector):
            reduced = partial_trace(state, list(range(n_qubits // 2, n_qubits)))
        elif isinstance(state, DensityMatrix):
            reduced = partial_trace(state, list(range(n_qubits // 2, n_qubits)))
        else:
            return None
        return float(np.real(entropy(reduced, base=2)))

    @staticmethod
    def summarize(
        state: StateLike,
        n_qubits: int,
        hamiltonian: SparsePauliOp,
        exact_state: Statevector | None = None,
        observable_bundle: ObservableBundle | None = None,
    ) -> Dict[str, object]:
        bundle = observable_bundle or ObservableFactory.default_bundle(n_qubits)
        entropy_value = StateAnalyzer.half_chain_entropy(state, n_qubits)
        energy_value = expectation(state, hamiltonian)
        variance_value = energy_variance(state, hamiltonian)
        energy_stddev = float(np.sqrt(max(variance_value, 0.0)))
        payload = {
            "energy": energy_value,
            "energy_variance": variance_value,
            "energy_stddev": energy_stddev,
            "relative_energy_stddev": energy_stddev / max(abs(float(energy_value)), 1e-12),
            "half_chain_entropy": entropy_value,
            "half_chain_entropy_mode": (
                "statevector" if isinstance(state, Statevector) and entropy_value is not None
                else "density_matrix" if isinstance(state, DensityMatrix) and entropy_value is not None
                else "disabled"
            ),
        }
        for name, observable in bundle.primary.items():
            value = expectation(state, observable)
            payload[name] = value
            if name == "x_parity":
                payload["x_even_sector_probability"] = 0.5 * (1.0 + value)
                payload["x_odd_sector_probability"] = 0.5 * (1.0 - value)
        for profile_name, observables in bundle.correlation_profiles.items():
            payload[profile_name] = [expectation(state, op) for _, op in observables]
        mx_profile = payload.get("magnetization_x_profile", [])
        mz_profile = payload.get("magnetization_z_profile", [])
        xx_profile = payload.get("correlation_xx_profile", [])
        zz_profile = payload.get("correlation_zz_profile", [])
        connected_xx = [
            float(pair - mx_profile[idx] * mx_profile[idx + 1])
            for idx, pair in enumerate(xx_profile)
        ] if mx_profile and xx_profile else []
        connected_zz = [
            float(pair - mz_profile[idx] * mz_profile[idx + 1])
            for idx, pair in enumerate(zz_profile)
        ] if mz_profile and zz_profile else []
        payload["connected_correlation_xx_profile"] = connected_xx
        payload["connected_correlation_zz_profile"] = connected_zz
        payload["connected_correlation_xx_mean"] = float(np.mean(connected_xx)) if connected_xx else None
        payload["connected_correlation_zz_mean"] = float(np.mean(connected_zz)) if connected_zz else None
        payload["fidelity_to_exact"] = float(np.real(state_fidelity(state, exact_state))) if exact_state is not None else None
        return payload

    @staticmethod
    def x_parity_projection(state: StateLike, n_qubits: int, sector: int = 1) -> tuple[DensityMatrix, float]:
        density = state if isinstance(state, DensityMatrix) else DensityMatrix(state)
        projector = ObservableFactory.projector_x_parity(n_qubits, sector=sector)
        raw = np.asarray(density.data, dtype=complex)
        numerator = projector @ raw @ projector
        rate = float(np.real(np.trace(numerator)))
        if rate <= 1e-12:
            return DensityMatrix(raw), 0.0
        return DensityMatrix(numerator / rate), rate

    @staticmethod
    def even_x_parity_projection(state: StateLike, n_qubits: int) -> tuple[DensityMatrix, float]:
        return StateAnalyzer.x_parity_projection(state, n_qubits, sector=1)


def observable_error_l2(summary: Dict[str, object], exact_summary: Dict[str, object], keys: Iterable[str]) -> float:
    squared = []
    for key in keys:
        if summary.get(key) is None or exact_summary.get(key) is None:
            continue
        squared.append((float(summary[key]) - float(exact_summary[key])) ** 2)
    return float(np.sqrt(np.mean(squared))) if squared else 0.0
