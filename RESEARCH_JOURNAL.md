# Research Journal

## 2026-03-12

I started this as a cleaner TFIM VQE benchmark and expected the main story to be ansatz quality versus noise. The first thing that bothered me was that the hardware-efficient ansatz kept winning too easily on raw energy, even in runs that felt too shallow to deserve it.

## 2026-03-19

I checked the parity bookkeeping expecting to find a bug and instead found the opposite: the ideal false-winner cases were real. The lower-energy state was buying that win by leaving the target `X`-parity sector, so I changed the selection logic to trust target-sector validity before filtered gap.

## 2026-04-11

Once I enforced the raw-sector validity rule consistently, the noisy wide sweep stopped looking gentle and collapsed into `valid_fraction = 0.000` in every noisy bucket. I kept that result instead of smoothing it away, because if the threshold is too strict or the physics is that fragile, that is the actual story.

## 2026-04-27

The live Runtime smoke test mattered less for the energy number than for the plumbing. I mostly wanted to know whether the observable remapping, transpilation width, and saved artifact path were trustworthy enough that a wider hardware campaign would mean anything.

## 2026-05-05

I finally stopped writing this repo like a white paper. The real value here is the sequence of judgment calls: when I decided energy was not enough, when I decided a false winner was still a failure under ideal execution, and when I admitted that the noisy validity rule currently gives a much harsher picture than I first expected.
