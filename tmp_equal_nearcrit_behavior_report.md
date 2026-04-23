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

- n=4, regime=near_critical, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=4.001540632200968, mean measurement s.e.=0.4674461031766122.
- n=4, regime=near_critical, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=3.6916505936497233, mean measurement s.e.=0.4784159653873395.
- n=6, regime=near_critical, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=7.693251768554329, mean measurement s.e.=0.6426226475837122.
- n=6, regime=near_critical, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=7.236566218834948, mean measurement s.e.=0.5760096434739613.

## Ansatz behavior

- ansatz=problem_inspired, regime=near_critical: raw wins=4, physics wins=4, budget wins=4, valid_fraction=0.000, fragility slope vs gate error=-76.65755882706263, behavior risk=6.775330016438471.

## Optimizer behavior

- optimizer=SPSA, regime=near_critical: physics wins=4, budget wins=4, mean filtered gap=5.655752303309992, mean cost s.e.=0.5411235899054063.

## Crossover integrity

- Total crossover buckets: 4
- Buckets where the raw energy winner differed from the physics winner: 0

## Deceptive low-energy cases

- Count: 0
