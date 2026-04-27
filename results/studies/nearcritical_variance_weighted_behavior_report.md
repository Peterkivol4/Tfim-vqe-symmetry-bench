# Detailed Behavior Study

This report summarizes how the TFIM VQE stack behaves across regimes, noise levels, ansatz families, optimizers, and execution-cost constraints.
It intentionally separates raw numerical winners from physically valid and budget-feasible winners.

## Behavior-analysis configuration

- weak_field_ratio=0.75
- near_critical_ratio=1.25
- low_noise_threshold=0.005
- moderate_noise_threshold=0.01
- behavior risk weights: symmetry=2.0, observable=0.25, uncertainty=0.5

## Regime-level behavior

- n=4, regime=near_critical, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=4.346792091716001, mean measurement s.e.=0.37576438798615736.
- n=4, regime=near_critical, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=5.211558371646996, mean measurement s.e.=0.4429728092206228.
- n=6, regime=near_critical, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=7.978169076794273, mean measurement s.e.=0.6490490339238632.
- n=6, regime=near_critical, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=6.685911069538113, mean measurement s.e.=0.5760667153977779.

## Ansatz behavior

- ansatz=problem_inspired, regime=near_critical: raw wins=4, physics wins=4, budget wins=4, valid_fraction=0.000, fragility slope vs gate error=-42.74917273251653, behavior risk=7.180133963806396.

## Optimizer behavior

- optimizer=SPSA, regime=near_critical: physics wins=4, budget wins=4, mean filtered gap=6.055607652423846, mean cost s.e.=0.5109632366321053.

## Crossover integrity

- Total crossover buckets: 4
- Buckets where the raw energy winner differed from the physics winner: 0

## Deceptive low-energy cases

- Count: 0
