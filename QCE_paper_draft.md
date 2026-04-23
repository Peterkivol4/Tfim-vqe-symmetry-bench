# Physics-Aware Benchmarking of Symmetry-Constrained Variational Quantum Eigensolvers for Transverse-Field Ising Chains Under Noise

**Target venue:** IEEE International Conference on Quantum Computing and Engineering (QCE)

## Abstract

Variational quantum eigensolvers (VQEs) remain among the most practical algorithmic candidates for near-term quantum hardware, but energy-only benchmarking obscures a central failure mode: shallow ans\"atze can report favorable energies while violating conserved structure of the target many-body problem. This manuscript studies that failure mode for the transverse-field Ising model (TFIM) using a software stack that augments conventional VQE evaluation with target-sector-aware symmetry diagnostics, observable-level error tracking, grouped measurement accounting, local readout mitigation, simulator-side zero-noise extrapolation (ZNE), and a runtime-oriented transpilation layer for IBM Quantum execution. The implementation is built in Python with Qiskit 2.3.1, Qiskit Aer 0.17.2, Qiskit Algorithms 0.4.0, and optional Qiskit IBM Runtime 0.46.1, with reproducible configuration files included in the repository requirements.

The central benchmark sweeps system size \(n \in \{4,6\}\), field strength \(g \in \{0.5,1.0,1.5\}\), gate error \(p \in \{0, 0.005, 0.01\}\), and three ansatz families: hardware-efficient, symmetry-preserving, and problem-inspired. The principal result is that physics-aware winner selection diverges from raw energy winner selection in \(4/18\) study buckets (false-winner rate \(= 0.222\)) [Table 1]. Under ideal simulation, the regime-level physically valid fraction is \(0.667\) across all retained regimes, whereas under the repository's current raw-sector threshold, every noisy regime collapses to \(0.000\) valid fraction [Table 2]. This is not a field-propagation bug. It is a scientifically meaningful consequence of the present validity rule, which requires the raw \(X\)-parity expectation to remain within a tolerance of 0.05 of the exact target sector.

The additional mitigation results are mixed rather than uniformly favorable. In a near-critical noisy SPSA comparison, variance-weighted shot allocation reduces mean measurement standard error from \(0.5411\) to \(0.5110\), but does not reduce mean exact gap [Table 3]. In a problem-inspired ZNE sweep, mitigation gain is positive in \(8/12\) runs with mean gain \(0.0755\), but negative in the remaining four runs [Table 4]. A live IBM Runtime smoke experiment on `ibm_fez` completes successfully after correcting ISA-observable width remapping and yields an exact-gap estimate of \(0.1178\) for a two-qubit TFIM instance [Table 5]. Collectively, these results support a narrower but stronger claim: physics-aware software instrumentation is itself a decisive variable in VQE benchmarking, and software-facing validity criteria can qualitatively change the interpretation of noisy variational studies.

## I. Introduction

The present generation of noisy quantum processors has renewed interest in variational quantum algorithms because they trade circuit depth for classical optimization and can, in principle, adapt to device noise [1], [2]. Among these algorithms, the variational quantum eigensolver (VQE) has become the canonical baseline for ground-state estimation in chemistry, lattice models, and condensed-matter toy problems [1], [3]. The transverse-field Ising model (TFIM) is especially attractive as a benchmark Hamiltonian because it is exactly solvable at modest sizes, exhibits physically interpretable regimes as \(g/J\) varies, and admits both shallow heuristic and structure-informed ansatz constructions.

However, the standard VQE reporting pattern remains underdetermined for serious benchmarking. It is no longer sufficient to state that one ansatz reaches a lower final energy than another. At minimum, a credible benchmark must answer the following questions. First, does the variational state remain in the correct symmetry sector of the target Hamiltonian? Second, are favorable energies preserved after symmetry filtering or are they artifacts of a physically invalid state? Third, how much of the reported advantage survives once grouped measurement overhead, shot-noise uncertainty, mitigation overhead, and transpilation-induced hardware cost are incorporated? Fourth, when a winner changes under a more physically informed objective, is the change attributable to meaningful many-body structure or to software-side bookkeeping?

The current repository addresses these questions for TFIM chains using a deliberately software-centric design. Each run records not only energy but also magnetization, nearest-neighbor correlators, connected correlators, \(X\)-parity expectation, parity-sector occupancy, fidelity to exact ground state when available, half-chain entropy when a full simulated state is available, energy variance, grouped-measurement metadata, shot-allocation details, and transpilation-derived hardware metrics [Listing 1], [Listing 2]. The study output then performs three distinct winner analyses for every \((n, g, p)\) bucket: the lowest-energy candidate, the physics-aware candidate, and the lowest-budget feasible candidate [Listing 2]. This separation is necessary because a low-energy candidate can be physically unfaithful and a physically faithful candidate can be operationally prohibitive.

The highest-value result of the retained dataset is not an unqualified positive outcome. Instead, it is the discovery that the software definition of physical validity dominates the interpretation of the noisy study. In the current implementation, a run is marked physically valid only if the raw symmetry-breaking error

\[
\epsilon_{\Pi_X} \equiv \max \left\{0, \frac{1 - s_\star \langle \Pi_X \rangle}{2} \right\}
\tag{1}
\]

stays below a user-configurable threshold \(\tau_{\mathrm{phys}}\), where \(s_\star \in \{-1,+1\}\) is the exact target \(X\)-parity sector inferred from exact diagonalization, and \(\Pi_X = \prod_i X_i\) is the global \(X\)-parity operator. With the default \(\tau_{\mathrm{phys}} = 0.05\), Eq. (1) implies that for the even sector one effectively requires \(\langle \Pi_X \rangle \ge 0.9\), equivalently target-sector occupancy of at least 0.95. In the retained noisy studies, that threshold is severe enough to drive regime-level valid fraction to zero even when symmetry-projected observables remain informative [Table 2].

This paper therefore makes a narrower but more rigorous claim than a typical "VQE improvement" report. The main contribution is not that every mitigation module helps. The main contribution is a reproducible software benchmark showing how symmetry-aware reporting, measurement architecture, and validity definitions reshape TFIM VQE conclusions.

### Contributions

- We implement a target-sector-aware TFIM VQE stack that aligns all parity diagnostics, projection summaries, and validity flags to the exact ground-state \(X\)-parity sector rather than assuming a fixed even sector.
- We introduce a crossover analysis that explicitly separates raw-energy winners from physics-aware and budget-aware winners, exposing false-winner buckets in \(4/18\) retained study points [Table 1].
- We show that under the repository's current raw-sector validity rule, ideal runs can remain mostly valid while all retained noisy regimes collapse to zero valid fraction [Table 2].
- We quantify the tradeoff between uncertainty reduction and solution quality for variance-weighted shot allocation, showing lower mean measurement standard error but no mean exact-gap improvement in the retained near-critical SPSA comparison [Table 3].
- We show that local ZNE in the retained problem-inspired sweep is beneficial on average but not uniformly beneficial across runs, with \(8/12\) positive mitigation gains and four negative cases [Table 4].
- We validate the repository's runtime-facing execution surface on a real IBM Quantum backend after correcting ISA-observable width remapping, obtaining a completed job on `ibm_fez` with exact gap \(0.1178\) [Table 5].

### Paper Outline

Section II reviews VQE benchmarking, symmetry handling, grouped measurements, and mitigation in the context of TFIM workloads. Section III formalizes the TFIM model, the parity-aware scoring rules, and the repository's physical-validity criterion. Section IV summarizes the software system design and cites the specific code paths that realize the validity rule, crossover selection, and runtime observable remapping. Section V reports the retained empirical results and interprets both positive and negative findings. The remaining sections of the full paper will expand this draft into a complete IEEE QCE submission with a broader literature base, full appendices, and camera-ready figure integration.

## II. Background and Related Work

### II.A. Variational Quantum Eigensolvers as NISQ Baselines

VQE was introduced as a hybrid quantum-classical strategy for estimating ground-state energies by minimizing the expectation value of a parameterized circuit with respect to a Hamiltonian \(H\) [1]. Since then, the algorithm family has expanded into a broad landscape of ansatz design, measurement reduction, error mitigation, and optimizer engineering [2], [3]. The key practical challenge is that favorable energy estimates alone do not certify physically faithful states. In lattice-model settings, this problem is amplified because the target Hamiltonian often has nontrivial symmetries, and hardware-efficient circuits can violate those symmetries while still reporting numerically attractive energies.

### II.B. Symmetry Awareness in Variational Algorithms

Symmetry verification, symmetry-preserving ansatz design, and post-selection are now standard tools for improving the physical faithfulness of variational algorithms [4]-[6]. Yet a gap remains between algorithmic proposals and software benchmarking practice. Many software studies report the final energy, optionally the final fidelity, and only later discuss symmetry qualitatively. This workflow obscures whether a nominal improvement reflects the target phase of the model or merely a symmetry-breaking variational shortcut. The present repository is explicitly designed to close that software gap by making target-sector inference, filtered observables, and parity-derived validity first-class outputs rather than after-the-fact diagnostics.

### II.C. Measurement Frugality and Shot Allocation

Measurement cost dominates many VQE workflows. Grouping Pauli terms into commuting or qubit-wise-commuting (QWC) sets reduces basis changes and shot fragmentation, while adaptive allocation seeks to assign larger shot budgets to higher-variance groups [7], [8]. The current implementation uses explicit QWC grouping and supports `equal`, `coefficient_weighted`, and `variance_weighted` allocation. This is important because the utility of a shot-allocation policy is not captured by energy alone; it must also be evaluated in terms of uncertainty, wall-clock cost, and induced bias in winner selection.

### II.D. Error Mitigation and Runtime Execution

Zero-noise extrapolation (ZNE) remains one of the most accessible error-mitigation primitives for near-term experiments [9], [10]. In the present repository, local ZNE is implemented as a simulator-side workflow that rescales gate error and gate duration while holding \(T_1\) and \(T_2\) fixed, then extrapolates grouped cost estimates back to zero noise. This is a practical but imperfect model, and the retained results show exactly why it must be evaluated empirically rather than assumed beneficial a priori [Table 4]. On the hardware side, IBM Runtime provides an execution surface for estimator-style expectation evaluation, but correct operation depends on careful observable remapping after transpilation. The runtime bug uncovered and corrected in this repository is therefore not a peripheral engineering detail; it is necessary to make hardware-side benchmarking interpretable [Listing 3].

## III. Theoretical Framework

### III.A. TFIM Hamiltonian and Symmetry

For an \(n\)-qubit chain with coupling strength \(J\) and transverse field \(g\), the repository studies the Hamiltonian

\[
H_{\mathrm{TFIM}} = -J \sum_{i=1}^{n-1} Z_i Z_{i+1} - g \sum_{i=1}^{n} X_i ,
\tag{2}
\]

with an optional periodic boundary term when enabled. The Hilbert space is \(\mathcal{H} = (\mathbb{C}^2)^{\otimes n}\). For the retained study artifacts analyzed in this draft, \(J=1\), \(n \in \{4,6\}\), and \(g \in \{0.5,1.0,1.5\}\).

The relevant global symmetry operator is

\[
\Pi_X = \prod_{i=1}^n X_i,
\tag{3}
\]

which defines even and odd parity sectors. Rather than hard-coding the even sector as physically correct, the repository infers the target sector

\[
s_\star = \mathrm{sign}\!\left(\langle \psi_0 | \Pi_X | \psi_0 \rangle\right)
\tag{4}
\]

from the exact ground state \(|\psi_0\rangle\) whenever exact diagonalization is available.

### III.B. Variational Objective and Physics-Aware Cost

For a parameterized circuit \(U(\theta)\) acting on \(|0\rangle^{\otimes n}\), the raw variational state is \(|\psi(\theta)\rangle = U(\theta)|0\rangle^{\otimes n}\), and the baseline optimization objective is the energy expectation

\[
E(\theta) = \langle \psi(\theta) | H_{\mathrm{TFIM}} | \psi(\theta) \rangle.
\tag{5}
\]

When a symmetry penalty is enabled, the repository instead minimizes

\[
C(\theta) = \langle H_{\mathrm{TFIM}} \rangle_\theta - \lambda \langle \Pi_X \rangle_\theta ,
\tag{6}
\]

which is equivalent, up to an additive constant, to a penalty on parity-sector violation.

### III.C. Raw Validity, Filtered Metrics, and Physics Score

The implementation distinguishes three related but non-identical notions of physical quality.

First, the **raw symmetry-breaking error** is defined by Eq. (1). A run is declared physically valid if

\[
\epsilon_{\Pi_X} \le \tau_{\mathrm{phys}},
\tag{7}
\]

with \(\tau_{\mathrm{phys}} = 0.05\) by default.

Second, the repository computes a symmetry-projected state \(\rho_{\mathrm{filt}}\) by projecting the raw state \(\rho\) onto the target sector:

\[
\rho_{\mathrm{filt}} = \frac{P_{s_\star} \rho P_{s_\star}}{\mathrm{Tr}(P_{s_\star}\rho P_{s_\star})},
\qquad
P_{s_\star} = \frac{I + s_\star \Pi_X}{2}.
\tag{8}
\]

This filtered state yields a **filtered exact gap** and filtered observable error. The symmetry projection rate

\[
r_{\Pi_X} = \mathrm{Tr}(P_{s_\star}\rho P_{s_\star})
\tag{9}
\]

is reported as `postselection_rate` in the implementation.

Third, the repository defines a **physics score**

\[
S_{\mathrm{phys}} = \Delta_{\mathrm{filt}} + w_{\Pi} \epsilon_{\Pi_X} + w_{\mathrm{obs}} \varepsilon_{\mathrm{obs}},
\tag{10}
\]

where \(\Delta_{\mathrm{filt}}\) is the filtered exact gap, \(\varepsilon_{\mathrm{obs}}\) is the filtered observable error, and \((w_{\Pi}, w_{\mathrm{obs}})\) are software-configurable penalty weights. The crucial methodological tension in this repository is that Eq. (7) is evaluated on the **raw** state, whereas Eq. (10) uses **filtered** quantities. This tension becomes central in the noisy regime.

## IV. Methodology and System Design

### IV.A. Software Stack and Experimental Surface

The retained repository uses Python with pinned requirements `numpy==2.3.5`, `scipy==1.17.0`, `matplotlib==3.10.8`, `qiskit==2.3.1`, `qiskit-aer==0.17.2`, and `qiskit-algorithms==0.4.0`; the optional runtime path uses `qiskit-ibm-runtime==0.46.1`. The local study path is the validated path for bulk sweeps. The IBM Runtime path is positioned as a preflight and integration layer rather than a replacement for the local simulator benchmark.

### IV.B. Listing 1: Raw-Sector Validity Computation

The core validity rule is implemented in [Listing 1].

**Listing 1.** Raw-sector physical-validity rule in `run_vqe()` (Python).

```python
x_parity = observables.get("x_parity")
symmetry_breaking_error = None if x_parity is None else float(
    max(0.0, 0.5 * (1.0 - float(self.target_x_parity_sector) * float(x_parity)))
)
physical_valid = None if symmetry_breaking_error is None else bool(
    symmetry_breaking_error <= physical_validity_tol
)
```

Lines 1-2 implement Eq. (1). The factor of \(1/2\) is not cosmetic: it converts parity expectation into a sector-occupancy deficit so that \(x\)-parity \(=1\) gives zero symmetry-breaking error, while \(x\)-parity \(=0.9\) corresponds to error \(0.05\). Line 3 then converts that continuous diagnostic into a hard boolean. This thresholding step is exactly where the noisy-study valid fractions collapse in the retained dataset.

### IV.C. Listing 2: Crossover Winner Selection

The study's central benchmark mechanism is the crossover selector in [Listing 2].

**Listing 2.** Crossover winner selection in `build_crossover()` (Python).

```python
energy_winner = min(bucket, key=lambda row: float(row["energy"]))
feasible_bucket = [row for row in bucket if bool(row.get("physical_valid"))]
candidate_bucket = feasible_bucket or bucket
physics_winner = min(
    candidate_bucket,
    key=lambda row: float(row["physics_score"])
)
budget_bucket = feasible_bucket or bucket
budget_winner = min(
    budget_bucket,
    key=lambda row: (
        float(row.get("estimated_total_shots_used") or 1e18),
        float(row.get("transpiled_two_qubit_gate_count") or 1e18),
        float(row.get("transpiled_depth") or 1e18),
        float(row.get("physics_score") or 1e18),
    ),
)
```

The important design choice is that `physics_winner` and `budget_winner` preferentially select from `feasible_bucket`, which depends on [Listing 1]. If the physical-validity rule is too strict, the algorithm silently falls back to the full bucket. Consequently, the reported crossover behavior is inseparable from the software definition of feasibility.

### IV.D. Listing 3: Runtime Observable Remapping

The hardware-facing runtime path depends on the observable-remapping logic in [Listing 3].

**Listing 3.** ISA observable remapping in `RuntimeFactory.apply_observable_layout()` (Python).

```python
observable_layout = RuntimeFactory._resolve_observable_layout(isa_circuit)
diagnostics = RuntimeFactory.layout_diagnostics(isa_circuit)
return {
    name: obs.apply_layout(observable_layout, num_qubits=isa_circuit.num_qubits)
    for name, obs in observables.items()
}, diagnostics
```

The explicit `num_qubits=isa_circuit.num_qubits` argument is essential. Without it, a two-qubit logical observable can remain at logical width after transpilation onto a wide backend, causing estimator submission failures. The live runtime smoke experiment in this repository exists specifically to validate this execution surface.

## V. Results and Analysis

### V.A. Principal Outcome: Physics-Aware and Raw-Energy Winners Disagree

The widest retained sweep is `tmp_wide_crossover`, comprising \(54\) runs and \(18\) crossover buckets over \(n \in \{4,6\}\), \(g \in \{0.5,1.0,1.5\}\), \(p \in \{0,0.005,0.01\}\), and three ansatz families with depth \(1\) and COBYLA optimization. In this sweep, the raw-energy winner and the physics-aware winner differ in \(4/18\) buckets, for a false-winner rate of \(0.222\) [Table 1]. This is the strongest retained empirical support for the repository's crossover narrative.

**Table 1.** Summary of the retained wide-crossover benchmark.

| Metric | Value |
|---|---:|
| Total crossover buckets | 18 |
| Buckets with raw-energy / physics-winner disagreement | 4 |
| False-winner rate | 0.222 |
| Mean physical-candidate count per bucket | 0.667 |

The existence of four disagreement buckets establishes that raw energy is not a sufficient ranking metric in this benchmark. However, the direction of the effect is more specific than the repository's original high-level prose suggested. In the retained data, the disagreement is concentrated in ideal buckets, while noisy buckets often have no physically valid candidates under the current threshold and therefore revert to fallback selection [Table 2].

### V.B. The Central Negative Result: Noisy Valid Fraction Collapses to Zero

Table 2 summarizes the regime-level behavior profiles from `tmp_wide_crossover_behavior_regimes.csv`. The ideal runs have valid fraction \(0.667\) across all retained regimes for both \(n=4\) and \(n=6\). By contrast, every retained noisy regime at \(p=0.005\) and \(p=0.01\) has valid fraction \(0.000\).

**Table 2.** Representative regime-level validity outcomes from the retained wide-crossover behavior report.

| \(n\) | Regime | Gate error \(p\) | Noise label | Valid fraction | False-winner rate | Mean filtered exact gap |
|---:|---|---:|---|---:|---:|---:|
| 4 | near-critical | 0.000 | ideal | 0.667 | 0.000 | 1.4043 |
| 4 | near-critical | 0.005 | low-noise | 0.000 | 0.000 | 1.6939 |
| 4 | near-critical | 0.010 | moderate-noise | 0.000 | 0.000 | 1.9111 |
| 6 | weak-field | 0.000 | ideal | 0.667 | 1.000 | 3.0303 |
| 6 | weak-field | 0.005 | low-noise | 0.000 | 0.000 | 3.3744 |
| 6 | weak-field | 0.010 | moderate-noise | 0.000 | 0.000 | 3.6666 |

This result must be interpreted carefully. It does **not** imply that all noisy states are physically meaningless. Instead, it implies that the repository's current raw-sector threshold is severe. For example, in the same wide sweep the mean target-sector probability is \(0.776\) at \(p=0.005\) and \(0.693\) at \(p=0.01\), while the mean sampled postselection rates are \(0.767\) and \(0.694\), respectively. These values indicate partial but non-negligible sector retention. They fail only because the default validity threshold corresponds to requiring target-sector probability near \(0.95\).

### V.C. Ansatz Dependence of the Validity Collapse

The ansatz-resolved means reveal a more nuanced story than the aggregate zero-valid-fraction headline. In the ideal regime, the symmetry-preserving and problem-inspired ans\"atze each have valid fraction \(1.0\), while the hardware-efficient ansatz has valid fraction \(0.0\). Under noise, all three families lose raw validity, but at different rates. At \(p=0.005\), the symmetry-preserving ansatz has mean symmetry-breaking error \(0.1216\), the problem-inspired ansatz \(0.1938\), and the hardware-efficient ansatz \(0.3573\). Thus, the noisy zero-valid-fraction result does not erase ansatz structure; it compresses a gradient of symmetry robustness into a binary outcome because the threshold is too strict for the noise model used in the retained sweeps.

### V.D. Shot Allocation and ZNE Are Mixed Interventions, Not Uniform Improvements

The retained near-critical SPSA comparison isolates shot-allocation strategy. Variance-weighted allocation reduces mean measurement standard error from \(0.5411\) to \(0.5110\), but the mean exact gap increases from \(5.7371\) to \(5.9864\) [Table 3]. Therefore, lower uncertainty did not translate into lower error in this bounded experiment.

**Table 3.** Near-critical SPSA comparison of shot-allocation strategies.

| Strategy | Mean measurement standard error | Mean exact gap |
|---|---:|---:|
| equal | 0.5411 | 5.7371 |
| variance_weighted | 0.5110 | 5.9864 |

The retained ZNE experiment is similarly mixed. In `tmp_zne_problem_raw.csv`, ZNE mitigation gain is positive in \(8/12\) runs and negative in \(4/12\), with mean gain \(0.0755\), minimum \(-0.2969\), and maximum \(0.4688\) [Table 4]. The correct interpretation is not that ZNE fails categorically, but that the current simulator-side workflow is regime dependent and can overshoot.

**Table 4.** Summary of retained problem-inspired ZNE outcomes.

| Metric | Value |
|---|---:|
| Runs | 12 |
| Positive mitigation gains | 8 |
| Negative mitigation gains | 4 |
| Mean mitigation gain | 0.0755 |
| Minimum mitigation gain | -0.2969 |
| Maximum mitigation gain | 0.4688 |

### V.E. Runtime Integration Result

The repository also contains a live runtime smoke artifact that validates the estimator execution path after correcting ISA observable remapping. The completed job ran on `ibm_fez` through the IBM Quantum Platform open plan, executed in direct job mode, and returned a two-qubit TFIM energy estimate of \(-2.1182\) with exact gap \(0.1178\) and reported standard deviation \(0.1454\) [Table 5]. The ISA circuit and remapped observable were both expanded to width \(156\), matching backend width and thereby confirming the correctness of the remapping patch.

**Table 5.** Live IBM Runtime smoke result from `tmp_live_runtime_smoke.json`.

| Field | Value |
|---|---|
| Backend | `ibm_fez` |
| Channel | `ibm_quantum_platform` |
| Execution mode | `job` |
| Job status | `DONE` |
| Job ID | `d7i64ci2khts739qgpng` |
| Estimated energy | -2.1182 |
| Exact gap | 0.1178 |
| Reported standard deviation | 0.1454 |
| ISA circuit width | 156 |
| ISA observable width | 156 |

## References

[1] A. Peruzzo *et al.*, "A variational eigenvalue solver on a photonic quantum processor," *Nature Communications*, vol. 5, Art. no. 4213, 2014.

[2] M. Cerezo *et al.*, "Variational quantum algorithms," *Nature Reviews Physics*, vol. 3, pp. 625-644, 2021.

[3] K. Bharti *et al.*, "Noisy intermediate-scale quantum algorithms," *Reviews of Modern Physics*, vol. 94, no. 1, Art. no. 015004, 2022.

[4] B. Gard *et al.*, "Efficient symmetry-preserving state preparation circuits for the variational quantum eigensolver algorithm," *npj Quantum Information*, vol. 6, Art. no. 10, 2020.

[5] S. C. Benjamin *et al.*, "Symmetry verification for variational quantum simulation," arXiv:2005.02756, 2020.

[6] G. S. Barron *et al.*, "Preserving symmetries for variational quantum eigensolvers in the presence of noise," *PRX Quantum*, vol. 2, Art. no. 030318, 2021.

[7] V. Verteletskyi, T.-C. Yen, and A. F. Izmaylov, "Measurement optimization in the variational quantum eigensolver using a minimum clique cover," *Journal of Chemical Physics*, vol. 152, Art. no. 124114, 2020.

[8] T.-C. Yen, V. Verteletskyi, and A. F. Izmaylov, "Measuring all compatible operators in one series of single-qubit measurements using unitary transformations," *Journal of Chemical Theory and Computation*, vol. 16, no. 4, pp. 2400-2409, 2020.

[9] K. Temme, S. Bravyi, and J. M. Gambetta, "Error mitigation for short-depth quantum circuits," *Physical Review Letters*, vol. 119, Art. no. 180509, 2017.

[10] A. Giurgica-Tiron *et al.*, "Digital zero noise extrapolation for quantum error mitigation," in *Proc. IEEE Int. Conf. Quantum Computing and Engineering (QCE)*, 2020, pp. 306-316.
