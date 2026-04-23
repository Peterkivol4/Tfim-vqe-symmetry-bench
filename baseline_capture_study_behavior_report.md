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

- n=4, regime=near_critical, noise=ideal (gate_error=0.0000): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=hardware_efficient, dominant budget winner=hardware_efficient, mean filtered gap=1.5468758115498789, mean measurement s.e.=None.

## Ansatz behavior

- ansatz=hardware_efficient, regime=near_critical: raw wins=1, physics wins=1, budget wins=1, valid_fraction=0.000, fragility slope vs gate error=None, behavior risk=2.7242574685005922.

## Optimizer behavior

- optimizer=COBYLA, regime=near_critical: physics wins=1, budget wins=1, mean filtered gap=1.5468758115498789, mean cost s.e.=None.

## Crossover integrity

- Total crossover buckets: 1
- Buckets where the raw energy winner differed from the physics winner: 0

## Deceptive low-energy cases

- Count: 0
