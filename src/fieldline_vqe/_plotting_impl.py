from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt

from .results import TrialRecord


class PlotBook:
    @staticmethod
    def save_single_run(prefix: Path, exact_energy: float, results: Dict[str, TrialRecord]) -> None:
        if not results:
            return
        fig, axes = plt.subplots(2, 2, figsize=(13, 9))
        records = list(results.values())
        labels = [r.label for r in records]
        for result in records:
            axes[0, 0].plot(result.energy_history, label=f"{result.label} (cost={result.cost_value:.4f})")
        axes[0, 0].axhline(exact_energy, linestyle="--", color="black", label="Exact energy")
        axes[0, 0].set_title("Objective convergence")
        axes[0, 0].set_xlabel("Evaluation")
        axes[0, 0].set_ylabel("Objective value")
        axes[0, 0].grid(alpha=0.3)
        legend_handles, legend_labels = axes[0, 0].get_legend_handles_labels()
        if legend_handles:
            axes[0, 0].legend()
        raw = [r.exact_gap for r in records]
        filt = [r.filtered_exact_gap if r.filtered_exact_gap is not None else r.exact_gap for r in records]
        axes[0, 1].bar(range(len(labels)), raw, label="raw")
        axes[0, 1].bar(range(len(labels)), filt, alpha=0.5, label="filtered")
        axes[0, 1].set_yscale("log")
        axes[0, 1].set_title("Raw vs filtered exact gap")
        axes[0, 1].set_ylabel("|E - E_exact|")
        axes[0, 1].set_xticks(range(len(labels)))
        axes[0, 1].set_xticklabels(labels, rotation=30, ha="right")
        axes[0, 1].grid(alpha=0.3)
        axes[0, 1].legend()
        symmetry_break = [r.symmetry_breaking_error if r.symmetry_breaking_error is not None else 0.0 for r in records]
        rates = [r.symmetry_postselection_rate if r.symmetry_postselection_rate is not None else 0.0 for r in records]
        axes[1, 0].bar(range(len(labels)), symmetry_break, label="symmetry-breaking error")
        axes[1, 0].plot(range(len(labels)), rates, marker="o", linestyle="--", label="projection retention")
        axes[1, 0].set_title("Symmetry quality")
        axes[1, 0].set_xticks(range(len(labels)))
        axes[1, 0].set_xticklabels(labels, rotation=30, ha="right")
        axes[1, 0].grid(alpha=0.3)
        legend_handles, legend_labels = axes[1, 0].get_legend_handles_labels()
        if legend_handles:
            axes[1, 0].legend()
        raw_obs = [r.observable_error_l2 if r.observable_error_l2 is not None else 0.0 for r in records]
        filt_obs = [r.filtered_observable_error_l2 if r.filtered_observable_error_l2 is not None else x for r, x in zip(records, raw_obs)]
        axes[1, 1].bar(range(len(labels)), raw_obs, label="raw")
        axes[1, 1].bar(range(len(labels)), filt_obs, alpha=0.5, label="filtered")
        axes[1, 1].set_title("Observable error vs exact reference")
        axes[1, 1].set_ylabel("L2 error")
        axes[1, 1].set_xticks(range(len(labels)))
        axes[1, 1].set_xticklabels(labels, rotation=30, ha="right")
        axes[1, 1].grid(alpha=0.3)
        axes[1, 1].legend()
        plt.tight_layout()
        plt.savefig(prefix.with_suffix('.png'), dpi=180, bbox_inches='tight')
        plt.close(fig)

    @staticmethod
    def save_study(prefix: Path, aggregate_rows: List[Dict[str, object]]) -> None:
        if not aggregate_rows:
            return
        fig, axes = plt.subplots(2, 2, figsize=(13, 9))
        ansatzes = sorted({str(r['ansatz']) for r in aggregate_rows})
        fields = sorted({float(r['field_strength']) for r in aggregate_rows})
        noises = sorted({float(r['gate_error']) for r in aggregate_rows})
        sizes = sorted({int(r['n_qubits']) for r in aggregate_rows})
        mid_field = fields[len(fields) // 2]
        noisy = noises[min(1, len(noises) - 1)]
        for ansatz in ansatzes:
            rows = [r for r in aggregate_rows if r['ansatz'] == ansatz and float(r['gate_error']) == 0.0 and int(r['depth']) == min(int(x['depth']) for x in aggregate_rows if x['ansatz'] == ansatz)]
            rows = sorted(rows, key=lambda r: (int(r['n_qubits']), float(r['field_strength'])))
            if rows:
                axes[0, 0].plot([f"n{int(r['n_qubits'])}, h={float(r['field_strength']):.2f}" for r in rows], [float(r['mean_exact_gap']) for r in rows], marker='o', label=ansatz)
        axes[0, 0].set_title('Field-strength sweep at zero noise')
        axes[0, 0].set_ylabel('Mean exact gap')
        axes[0, 0].tick_params(axis='x', rotation=40)
        axes[0, 0].grid(alpha=0.3)
        legend_handles, legend_labels = axes[0, 0].get_legend_handles_labels()
        if legend_handles:
            axes[0, 0].legend()
        for ansatz in ansatzes:
            rows = [r for r in aggregate_rows if r['ansatz'] == ansatz and int(r['n_qubits']) == sizes[0] and float(r['field_strength']) == mid_field and int(r['depth']) == min(int(x['depth']) for x in aggregate_rows if x['ansatz'] == ansatz)]
            rows = sorted(rows, key=lambda r: float(r['gate_error']))
            if rows:
                xs = [float(r['gate_error']) for r in rows]
                y = [float(r['mean_exact_gap']) for r in rows]
                yf = [float(r['mean_filtered_exact_gap']) if r['mean_filtered_exact_gap'] is not None else float(r['mean_exact_gap']) for r in rows]
                axes[0, 1].plot(xs, y, marker='o', label=f'{ansatz} raw')
                axes[0, 1].plot(xs, yf, marker='s', linestyle='--', label=f'{ansatz} filtered')
        axes[0, 1].set_title('Noise scaling and symmetry filtering')
        axes[0, 1].set_xlabel('Gate error')
        axes[0, 1].set_ylabel('Mean exact gap')
        axes[0, 1].grid(alpha=0.3)
        axes[0, 1].legend(ncols=2, fontsize=8)
        for ansatz in ansatzes:
            rows = [r for r in aggregate_rows if r['ansatz'] == ansatz and float(r['gate_error']) == 0.0 and float(r['field_strength']) == mid_field and int(r['depth']) == min(int(x['depth']) for x in aggregate_rows if x['ansatz'] == ansatz)]
            rows = sorted(rows, key=lambda r: int(r['n_qubits']))
            if rows:
                axes[1, 0].plot([int(r['n_qubits']) for r in rows], [float(r['mean_fidelity_to_exact']) if r['mean_fidelity_to_exact'] is not None else 0.0 for r in rows], marker='o', label=ansatz)
        axes[1, 0].set_title('System-size scaling')
        axes[1, 0].set_xlabel('Qubits')
        axes[1, 0].set_ylabel('Mean fidelity to exact')
        axes[1, 0].grid(alpha=0.3)
        legend_handles, legend_labels = axes[1, 0].get_legend_handles_labels()
        if legend_handles:
            axes[1, 0].legend()
        for ansatz in ansatzes:
            rows = [r for r in aggregate_rows if r['ansatz'] == ansatz and float(r['gate_error']) == noisy and int(r['n_qubits']) == sizes[0] and float(r['field_strength']) == mid_field]
            rows = sorted(rows, key=lambda r: int(r['depth']))
            if rows:
                axes[1, 1].plot([int(r['depth']) for r in rows], [float(r['mean_symmetry_breaking_error']) if r['mean_symmetry_breaking_error'] is not None else 0.0 for r in rows], marker='o', label=ansatz)
        axes[1, 1].set_title('Depth vs symmetry breaking')
        axes[1, 1].set_xlabel('Ansatz depth')
        axes[1, 1].set_ylabel('Mean symmetry-breaking error')
        axes[1, 1].grid(alpha=0.3)
        axes[1, 1].legend()
        plt.tight_layout()
        plt.savefig(prefix.with_suffix('.png'), dpi=180, bbox_inches='tight')
        plt.close(fig)


__all__ = ["PlotBook"]
