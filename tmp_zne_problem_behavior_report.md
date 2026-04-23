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

- n=4, regime=near_critical, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=4.033050519272955, mean measurement s.e.=0.5100312107484207.
- n=4, regime=near_critical, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=4.682360060409509, mean measurement s.e.=0.5032851065127002.
- n=4, regime=strong_field, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=6.340107039025085, mean measurement s.e.=0.5793905068043487.
- n=4, regime=strong_field, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=6.184858153585212, mean measurement s.e.=0.5885877563074176.
- n=4, regime=weak_field, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=3.4396432001665636, mean measurement s.e.=0.39404750665370286.
- n=4, regime=weak_field, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=2.9363823172648353, mean measurement s.e.=0.3689287172849248.
- n=6, regime=near_critical, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=6.3180742238122765, mean measurement s.e.=0.5375317941177992.
- n=6, regime=near_critical, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=6.588927628949074, mean measurement s.e.=0.5227957820100503.
- n=6, regime=strong_field, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=9.916863482261459, mean measurement s.e.=0.8134009428012732.
- n=6, regime=strong_field, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=9.400684853657172, mean measurement s.e.=0.7254065064564661.
- n=6, regime=weak_field, noise=low_noise (gate_error=0.0050): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=5.08408957048893, mean measurement s.e.=0.4215493534829285.
- n=6, regime=weak_field, noise=moderate_noise (gate_error=0.0100): valid_fraction=0.000, false_winner_rate=0.000, dominant physics winner=problem_inspired, dominant budget winner=problem_inspired, mean filtered gap=5.571510575179964, mean measurement s.e.=0.5082029748750739.

## Ansatz behavior

- ansatz=problem_inspired, regime=near_critical: raw wins=12, physics wins=12, budget wins=12, valid_fraction=0.000, fragility slope vs gate error=92.01629462733524, behavior risk=6.522851092496067.
- ansatz=problem_inspired, regime=strong_field: raw wins=12, physics wins=12, budget wins=12, valid_fraction=0.000, fragility slope vs gate error=-67.14275140441598, behavior risk=9.185718105027078.
- ansatz=problem_inspired, regime=weak_field: raw wins=12, physics wins=12, budget wins=12, valid_fraction=0.000, fragility slope vs gate error=-1.583987821069499, behavior risk=5.309747528745215.

## Optimizer behavior

- optimizer=SPSA, regime=near_critical: physics wins=12, budget wins=12, mean filtered gap=5.405603108110953, mean cost s.e.=0.5184109733472426.
- optimizer=SPSA, regime=strong_field: physics wins=12, budget wins=12, mean filtered gap=7.9606283821322315, mean cost s.e.=0.6766964280923764.
- optimizer=SPSA, regime=weak_field: physics wins=12, budget wins=12, mean filtered gap=4.257906415775073, mean cost s.e.=0.4231821380741575.

## Crossover integrity

- Total crossover buckets: 12
- Buckets where the raw energy winner differed from the physics winner: 0

## Deceptive low-energy cases

- Count: 0
