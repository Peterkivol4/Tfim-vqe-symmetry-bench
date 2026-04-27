from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fieldline_vqe.config import NoiseDeck, RunSpec, StudySpec
from fieldline_vqe.pipeline import run_experiment, run_study


def capture(prefix: str) -> dict[str, object]:
    base = Path(prefix)
    base.parent.mkdir(parents=True, exist_ok=True)
    single_prefix = str(base.with_name(base.name + '_single'))
    study_prefix = str(base.with_name(base.name + '_study'))
    zne_prefix = str(base.with_name(base.name + '_zne'))

    single = run_experiment(
        RunSpec(n_qubits=4, field_strength=1.0, ansatz='hardware_efficient', depth=1, optimizer='COBYLA', max_iter=2, verification_shots=32, seed=17, output_prefix=single_prefix),
        NoiseDeck(gate_error=0.0, seed=17),
    )
    study = run_study(
        StudySpec(system_sizes=[4], field_strengths=[1.0], depths=[1], ansatzes=['hardware_efficient'], optimizers=['COBYLA'], gate_errors=[0.0], seeds=[17], max_iter=2, verification_shots=32, output_prefix=study_prefix),
        NoiseDeck(gate_error=0.0, seed=17),
    )
    zne = run_experiment(
        RunSpec(n_qubits=4, field_strength=1.0, ansatz='hardware_efficient', depth=1, optimizer='SPSA', max_iter=1, verification_shots=16, seed=17, output_prefix=zne_prefix, use_noise=True, enable_zne=True, zne_factors=[1, 3], preflight_shots=8, base_shots=8, final_shots=16),
        NoiseDeck(gate_error=0.01, seed=17),
    )

    crossover = study.get('crossover', []) if isinstance(study, dict) else []
    rows = study.get('rows', []) if isinstance(study, dict) else []
    payload = {
        'single': {
            'label': single.label,
            'energy_gap': single.exact_gap,
            'symmetry_breaking_error': single.symmetry_breaking_error,
        },
        'study': {
            'rows': len(rows),
            'physics_winner': crossover[0]['physics_winner_label'] if crossover else None,
        },
        'zne': {
            'label': zne.label,
            'cost_value': zne.cost_value,
            'mitigation_gain': zne.mitigation_gain,
        },
    }
    out_path = base.with_suffix('.json')
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description='Capture a repeatable fieldline_vqe baseline payload.')
    parser.add_argument('--output-prefix', type=str, default=str(ROOT / 'results' / 'baselines' / 'baseline_capture'))
    args = parser.parse_args()
    capture(args.output_prefix)


if __name__ == '__main__':
    main()
