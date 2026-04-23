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

- n=4, regime=near_critical, noise=ideal (gate_error=0.0000): valid_fraction=0.667, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=1.4386563450624852, mean measurement s.e.=None.
- n=4, regime=near_critical, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=1.6501726674297117, mean measurement s.e.=0.05498234345112565.
- n=4, regime=near_critical, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=1.9095303823197844, mean measurement s.e.=0.05721115277949133.
- n=4, regime=strong_field, noise=ideal (gate_error=0.0000): valid_fraction=0.667, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=1.9347096369755192, mean measurement s.e.=None.
- n=4, regime=strong_field, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=1.8341310446221017, mean measurement s.e.=0.07489635973129154.
- n=4, regime=strong_field, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=2.4084766180015142, mean measurement s.e.=0.07888728132735678.
- n=4, regime=weak_field, noise=ideal (gate_error=0.0000): valid_fraction=0.667, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=0.9736590215912818, mean measurement s.e.=None.
- n=4, regime=weak_field, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=1.2374477768558239, mean measurement s.e.=0.03893110977831825.
- n=4, regime=weak_field, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=1.4325275933497577, mean measurement s.e.=0.04093737001631675.
- n=6, regime=near_critical, noise=ideal (gate_error=0.0000): valid_fraction=0.667, false_winner_rate=1.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=4.022130476579125, mean measurement s.e.=None.
- n=6, regime=near_critical, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=hardware_efficient, dominant budget winner=symmetry_preserving, mean filtered gap=3.973592376100645, mean measurement s.e.=0.06985917832400727.
- n=6, regime=near_critical, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=1.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=4.716825704862802, mean measurement s.e.=0.06949462966460007.
- n=6, regime=strong_field, noise=ideal (gate_error=0.0000): valid_fraction=0.667, false_winner_rate=1.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=5.101912229077139, mean measurement s.e.=None.
- n=6, regime=strong_field, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=hardware_efficient, dominant budget winner=symmetry_preserving, mean filtered gap=5.274003807830712, mean measurement s.e.=0.08628160122936698.
- n=6, regime=strong_field, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=hardware_efficient, dominant budget winner=symmetry_preserving, mean filtered gap=5.9817166272767395, mean measurement s.e.=0.0868081789639672.
- n=6, regime=weak_field, noise=ideal (gate_error=0.0000): valid_fraction=0.667, false_winner_rate=1.000, dominant physics winner=symmetry_preserving, dominant budget winner=symmetry_preserving, mean filtered gap=3.0053719504542955, mean measurement s.e.=None.
- n=6, regime=weak_field, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=hardware_efficient, dominant budget winner=symmetry_preserving, mean filtered gap=3.3548695677421825, mean measurement s.e.=0.05235653133820225.
- n=6, regime=weak_field, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=hardware_efficient, dominant budget winner=symmetry_preserving, mean filtered gap=3.5591921236134776, mean measurement s.e.=0.05415171759541928.

## Ansatz behavior

- ansatz=hardware_efficient, regime=near_critical: raw wins=9, physics wins=5, budget wins=0, valid_fraction=0.000, fragility slope vs gate error=85.24853839482027, behavior risk=3.257603478305483.
- ansatz=hardware_efficient, regime=strong_field: raw wins=9, physics wins=5, budget wins=0, valid_fraction=0.000, fragility slope vs gate error=185.6595434165542, behavior risk=4.226197408352791.
- ansatz=hardware_efficient, regime=weak_field: raw wins=9, physics wins=5, budget wins=0, valid_fraction=0.000, fragility slope vs gate error=64.18616921107304, behavior risk=2.1306399583436733.
- ansatz=problem_inspired, regime=near_critical: raw wins=0, physics wins=0, budget wins=0, valid_fraction=0.333, fragility slope vs gate error=47.06280437123636, behavior risk=4.361938979376527.
- ansatz=problem_inspired, regime=strong_field: raw wins=0, physics wins=0, budget wins=0, valid_fraction=0.333, fragility slope vs gate error=-38.68279375768342, behavior risk=4.6792743667851635.
- ansatz=problem_inspired, regime=weak_field: raw wins=0, physics wins=0, budget wins=0, valid_fraction=0.333, fragility slope vs gate error=63.837887238227964, behavior risk=3.7487615904232148.
- ansatz=symmetry_preserving, regime=near_critical: raw wins=9, physics wins=13, budget wins=18, valid_fraction=0.333, fragility slope vs gate error=42.52404706508991, behavior risk=2.9377111483512373.
- ansatz=symmetry_preserving, regime=strong_field: raw wins=9, physics wins=13, budget wins=18, valid_fraction=0.333, fragility slope vs gate error=56.0589572249686, behavior risk=4.050933610843992.
- ansatz=symmetry_preserving, regime=weak_field: raw wins=9, physics wins=13, budget wins=18, valid_fraction=0.333, fragility slope vs gate error=23.879255288347693, behavior risk=2.4056718402471344.

## Optimizer behavior

- optimizer=COBYLA, regime=near_critical: physics wins=18, budget wins=18, mean filtered gap=2.9518179920590923, mean cost s.e.=0.06288682605480608.
- optimizer=COBYLA, regime=strong_field: physics wins=18, budget wins=18, mean filtered gap=3.7558249939639543, mean cost s.e.=0.08171835531299562.
- optimizer=COBYLA, regime=weak_field: physics wins=18, budget wins=18, mean filtered gap=2.26051133893447, mean cost s.e.=0.04659418218206413.

## Crossover integrity

- Total crossover buckets: 18
- Buckets where the raw energy winner differed from the physics winner: 4

## Deceptive low-energy cases

- Count: 0
