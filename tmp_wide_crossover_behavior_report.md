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

- n=4, regime=near_critical, noise=ideal (gate_error=0.0000): valid_fraction=0.667, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=1.404268506585377, mean measurement s.e.=None.
- n=4, regime=near_critical, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=1.6939375988479084, mean measurement s.e.=0.054964617190044626.
- n=4, regime=near_critical, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=1.9110588715909491, mean measurement s.e.=0.05663098393499029.
- n=4, regime=strong_field, noise=ideal (gate_error=0.0000): valid_fraction=0.667, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=2.059440414008255, mean measurement s.e.=None.
- n=4, regime=strong_field, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=2.023437137689776, mean measurement s.e.=0.07710561103188644.
- n=4, regime=strong_field, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=2.4126749541937564, mean measurement s.e.=0.07783419234469623.
- n=4, regime=weak_field, noise=ideal (gate_error=0.0000): valid_fraction=0.667, false_winner_rate=1.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=0.9910352192569768, mean measurement s.e.=None.
- n=4, regime=weak_field, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=1.1727148058018513, mean measurement s.e.=0.03823743473941593.
- n=4, regime=weak_field, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=1.3724569919638852, mean measurement s.e.=0.04089676137854867.
- n=6, regime=near_critical, noise=ideal (gate_error=0.0000): valid_fraction=0.667, false_winner_rate=1.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=4.005479592692707, mean measurement s.e.=None.
- n=6, regime=near_critical, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=hardware_efficient, dominant budget winner=symmetry_preserving, mean filtered gap=3.9365603251093244, mean measurement s.e.=0.06959305412787177.
- n=6, regime=near_critical, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=hardware_efficient, dominant budget winner=symmetry_preserving, mean filtered gap=4.5263151287889505, mean measurement s.e.=0.06940775102739541.
- n=6, regime=strong_field, noise=ideal (gate_error=0.0000): valid_fraction=0.667, false_winner_rate=1.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=5.029866258067786, mean measurement s.e.=None.
- n=6, regime=strong_field, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=hardware_efficient, dominant budget winner=symmetry_preserving, mean filtered gap=5.287609718461138, mean measurement s.e.=0.08588464825180504.
- n=6, regime=strong_field, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=hardware_efficient, dominant budget winner=symmetry_preserving, mean filtered gap=6.005277517259444, mean measurement s.e.=0.08586259660879426.
- n=6, regime=weak_field, noise=ideal (gate_error=0.0000): valid_fraction=0.667, false_winner_rate=1.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=3.0302945593958683, mean measurement s.e.=None.
- n=6, regime=weak_field, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=hardware_efficient, dominant budget winner=symmetry_preserving, mean filtered gap=3.3744089635679764, mean measurement s.e.=0.05214821283248308.
- n=6, regime=weak_field, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=hardware_efficient, dominant budget winner=symmetry_preserving, mean filtered gap=3.6666259149365397, mean measurement s.e.=0.05354367870057068.

## Ansatz behavior

- ansatz=hardware_efficient, regime=near_critical: raw wins=10, physics wins=6, budget wins=0, valid_fraction=0.000, fragility slope vs gate error=65.2600209383841, behavior risk=3.2129819493656666.
- ansatz=hardware_efficient, regime=strong_field: raw wins=10, physics wins=6, budget wins=0, valid_fraction=0.000, fragility slope vs gate error=181.5460093380395, behavior risk=4.446709484453949.
- ansatz=hardware_efficient, regime=weak_field: raw wins=10, physics wins=6, budget wins=0, valid_fraction=0.000, fragility slope vs gate error=65.2777323724873, behavior risk=2.2848668814723774.
- ansatz=problem_inspired, regime=near_critical: raw wins=0, physics wins=0, budget wins=0, valid_fraction=0.333, fragility slope vs gate error=46.68394781805509, behavior risk=4.358035514173262.
- ansatz=problem_inspired, regime=strong_field: raw wins=0, physics wins=0, budget wins=0, valid_fraction=0.333, fragility slope vs gate error=-38.49601096600531, behavior risk=4.6808201407238785.
- ansatz=problem_inspired, regime=weak_field: raw wins=0, physics wins=0, budget wins=0, valid_fraction=0.333, fragility slope vs gate error=63.46273923156684, behavior risk=3.745172401089309.
- ansatz=symmetry_preserving, regime=near_critical: raw wins=8, physics wins=12, budget wins=18, valid_fraction=0.333, fragility slope vs gate error=42.19991640883313, behavior risk=2.9362193555510943.
- ansatz=symmetry_preserving, regime=strong_field: raw wins=8, physics wins=12, budget wins=18, valid_fraction=0.333, fragility slope vs gate error=56.2468715345398, behavior risk=4.050871472103824.
- ansatz=symmetry_preserving, regime=weak_field: raw wins=8, physics wins=12, budget wins=18, valid_fraction=0.333, fragility slope vs gate error=23.92249763308274, behavior risk=2.4055756483799158.

## Optimizer behavior

- optimizer=COBYLA, regime=near_critical: physics wins=18, budget wins=18, mean filtered gap=2.912936670602536, mean cost s.e.=0.06264910157007553.
- optimizer=COBYLA, regime=strong_field: physics wins=18, budget wins=18, mean filtered gap=3.8030509999466924, mean cost s.e.=0.0816717620592955.
- optimizer=COBYLA, regime=weak_field: physics wins=18, budget wins=18, mean filtered gap=2.267922742487183, mean cost s.e.=0.04620652191275459.

## Crossover integrity

- Total crossover buckets: 18
- Buckets where the raw energy winner differed from the physics winner: 4

## Deceptive low-energy cases

- Count: 0
