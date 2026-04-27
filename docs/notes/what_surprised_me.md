# What Surprised Me In This Repo

## Unexpected result

The strongest false-winner cases in the retained wide sweep were not noisy at all. In `results/studies/wide_crossover_behavior_crossover.csv`, all `4/18` false-winner buckets came from the ideal depth-1 study, where the hardware-efficient ansatz lowered the raw energy by leaving the target `X`-parity sector instead of representing the right physical state.

## Constraint

Once I enforced the current raw-sector validity threshold, every noisy bucket in the retained wide sweep collapsed to `valid_fraction = 0.000`. That means the repo can honestly tell a strong false-winner story right now, but it cannot honestly claim a gentle noisy crossover in physical validity without either a tolerance sweep or a wider runtime campaign.

## Judgment call

I chose to trust target-sector validity before filtered gap. That means the physics-aware selector will sometimes prefer a candidate with worse raw energy and worse filtered gap if the lower-energy candidate only keeps about half of its probability mass in the target sector. I still think that is the right call for this repo, because otherwise the benchmark would reward states that solve the wrong problem.

## Next experiment

Repeat the exact false-winner buckets on a bounded runtime campaign with four settings:

- no mitigation
- symmetry penalty only
- readout mitigation only
- symmetry penalty plus ZNE

The question I want answered next is whether the shallow hardware-efficient ansatz can recover target-sector probability without giving back all of its raw-energy advantage.
