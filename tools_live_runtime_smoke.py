from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fieldline_vqe.ansatz import CircuitFactory
from fieldline_vqe.experiment import FieldLineExperiment
from fieldline_vqe.hamiltonian import SpinChainBuilder
from fieldline_vqe.runtime import RuntimeFactory

try:
    from qiskit_ibm_runtime import EstimatorV2, QiskitRuntimeService, Session
except Exception:
    EstimatorV2 = None
    QiskitRuntimeService = None
    Session = None

DEFAULT_CHANNELS = ("ibm_quantum_platform", "ibm_cloud", "ibm_quantum")
TOKEN_ENV_VARS = ("FIELDLINE_IBM_RUNTIME_TOKEN", "IBM_RUNTIME_TOKEN", "QISKIT_IBM_TOKEN")
PENDING_STATUSES = {"INITIALIZING", "QUEUED", "RUNNING", "VALIDATING"}


def ordered_channels(preferred_channel: str | None = None) -> list[str]:
    channels: list[str] = []
    if preferred_channel:
        channels.append(preferred_channel)
    for channel in DEFAULT_CHANNELS:
        if channel not in channels:
            channels.append(channel)
    return channels


def resolve_runtime_token() -> tuple[str, str]:
    for name in TOKEN_ENV_VARS:
        value = os.getenv(name)
        if value:
            return name, value
    joined = ", ".join(TOKEN_ENV_VARS)
    raise RuntimeError(f"set one of {joined} before running the live runtime smoke test")


def _status_name(status: Any) -> str | None:
    if status is None:
        return None
    return getattr(status, "name", str(status))


def _coerce_scalar(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if hasattr(value, "item"):
        try:
            return float(value.item())
        except Exception:
            pass
    if hasattr(value, "tolist"):
        try:
            value = value.tolist()
        except Exception:
            pass
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        return _coerce_scalar(value[0])
    try:
        return float(value)
    except Exception:
        return None


def _coerce_float_list(value: Any) -> list[float] | None:
    if value is None:
        return None
    if hasattr(value, "tolist"):
        try:
            value = value.tolist()
        except Exception:
            pass
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            scalar = _coerce_scalar(item)
            if scalar is not None:
                out.append(scalar)
        return out
    scalar = _coerce_scalar(value)
    return None if scalar is None else [scalar]


def write_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True))


def _connect_service(token: str, preferred_channel: str | None = None, instance: str | None = None) -> tuple[object, str]:
    if QiskitRuntimeService is None:
        raise ImportError("qiskit-ibm-runtime is required for live runtime smoke checks")
    failures: dict[str, str] = {}
    for channel in ordered_channels(preferred_channel):
        kwargs: dict[str, object] = {"channel": channel, "token": token}
        if instance:
            kwargs["instance"] = instance
        try:
            return QiskitRuntimeService(**kwargs), channel
        except Exception as exc:
            failures[channel] = f"{type(exc).__name__}: {exc}"
    detail = "; ".join(f"{channel} -> {message}" for channel, message in failures.items())
    raise RuntimeError(f"unable to connect to IBM Runtime using configured channels: {detail}")


def _select_backend(service, n_qubits: int, backend_name: str | None = None, instance: str | None = None):
    if backend_name:
        matches = service.backends(name=backend_name, instance=instance)
        if not matches:
            raise RuntimeError(f"backend '{backend_name}' not found for the configured IBM Runtime account")
        return matches[0]
    try:
        return service.least_busy(min_num_qubits=n_qubits, instance=instance, simulator=False, operational=True)
    except Exception:
        matches = service.backends(min_num_qubits=n_qubits, instance=instance, simulator=False, operational=True)
        if not matches:
            raise RuntimeError(f"no operational non-simulator backend found with at least {n_qubits} qubits")
        return matches[0]


def _open_session(service, backend):
    try:
        return Session(service=service, backend=backend)
    except TypeError:
        return Session(backend=backend)


def run_live_smoke(
    *,
    n_qubits: int = 2,
    field_strength: float = 1.0,
    coupling: float = 1.0,
    ansatz_name: str = "symmetry_preserving",
    depth: int = 1,
    precision: float = 0.2,
    seed: int = 11,
    timeout: int = 240,
    preferred_channel: str | None = None,
    backend_name: str | None = None,
    instance: str | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    if not RuntimeFactory.available() or EstimatorV2 is None or Session is None:
        raise ImportError("IBM Runtime support requires qiskit-ibm-runtime and configured credentials")

    token_env, token = resolve_runtime_token()
    service, channel = _connect_service(token, preferred_channel=preferred_channel, instance=instance)
    backend = _select_backend(service, n_qubits=n_qubits, backend_name=backend_name, instance=instance)

    hamiltonian = SpinChainBuilder.ising_chain(n_qubits, field_strength, coupling)
    experiment = FieldLineExperiment(hamiltonian, n_qubits, field_strength, coupling, seed=seed)
    ansatz = CircuitFactory.build(ansatz_name, n_qubits, depth)
    circuit = ansatz.assign_parameters([0.0] * ansatz.num_parameters)
    isa_circuit, isa_observables, layout_metadata = RuntimeFactory.transpile_to_isa(
        circuit,
        {"energy": hamiltonian},
        backend,
        optimization_level=0,
        seed_transpiler=seed,
    )

    report: dict[str, Any] = {
        "ansatz": ansatz_name,
        "backend": backend.name,
        "backend_num_qubits": int(getattr(backend, "num_qubits", 0)),
        "channel": channel,
        "comparison_ready": False,
        "coupling": float(coupling),
        "depth": int(depth),
        "execution_mode": None,
        "exact_ground_energy": float(experiment.exact_energy),
        "field_strength": float(field_strength),
        "instance": instance,
        "isa_circuit_num_qubits": int(isa_circuit.num_qubits),
        "isa_observable_num_qubits": int(isa_observables["energy"].num_qubits),
        "job_id": None,
        "job_status_after_submit": None,
        "job_status_final": None,
        "layout_metadata": layout_metadata,
        "n_qubits": int(n_qubits),
        "precision": float(precision),
        "result_available": False,
        "result_energy": None,
        "result_exact_gap": None,
        "result_stds": None,
        "seed": int(seed),
        "session_fallback_reason": None,
        "submitted_ok": False,
        "timeout_seconds": int(timeout),
        "token_env_var": token_env,
    }

    job = None
    execution_context = nullcontext(None)
    execution_mode = backend
    report["execution_mode"] = "job"
    try:
        session = _open_session(service, backend)
    except Exception as exc:
        report["session_fallback_reason"] = f"{type(exc).__name__}: {exc}"
    else:
        execution_context = session
        execution_mode = session
        report["execution_mode"] = "session"

    with execution_context as active_mode:
        estimator = EstimatorV2(mode=active_mode if active_mode is not None else execution_mode)
        try:
            job = estimator.run([(isa_circuit, isa_observables["energy"])], precision=precision)
            report["job_id"] = job.job_id()
            report["job_status_after_submit"] = _status_name(job.status())
            report["submitted_ok"] = True
            report["comparison_ready"] = report["isa_circuit_num_qubits"] == report["isa_observable_num_qubits"]

            result = job.result(timeout=timeout)
            report["job_status_final"] = _status_name(job.status())
            first = result[0]
            energy = _coerce_scalar(getattr(first.data, "evs", None))
            stds = _coerce_float_list(getattr(first.data, "stds", None))
            report["result_energy"] = energy
            report["result_stds"] = stds
            report["result_available"] = energy is not None
            if energy is not None:
                report["result_exact_gap"] = abs(energy - report["exact_ground_energy"])
        except Exception as exc:
            report["error_type"] = type(exc).__name__
            report["error_message"] = str(exc)
            if job is not None:
                report["job_status_final"] = _status_name(job.status())

    if output_path is not None:
        write_report(report, output_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an opt-in IBM Runtime smoke job and export a study-comparable JSON report.")
    parser.add_argument("--output", type=Path, default=Path("tmp_live_runtime_smoke.json"))
    parser.add_argument("--n-qubits", type=int, default=2)
    parser.add_argument("--field-strength", type=float, default=1.0)
    parser.add_argument("--coupling", type=float, default=1.0)
    parser.add_argument("--ansatz", type=str, default="symmetry_preserving")
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--precision", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--channel", type=str, default=os.getenv("FIELDLINE_VQE_RUNTIME_CHANNEL"))
    parser.add_argument("--backend", type=str, default=os.getenv("FIELDLINE_VQE_RUNTIME_BACKEND"))
    parser.add_argument("--instance", type=str, default=os.getenv("FIELDLINE_VQE_RUNTIME_INSTANCE"))
    args = parser.parse_args()

    report = run_live_smoke(
        n_qubits=args.n_qubits,
        field_strength=args.field_strength,
        coupling=args.coupling,
        ansatz_name=args.ansatz,
        depth=args.depth,
        precision=args.precision,
        seed=args.seed,
        timeout=args.timeout,
        preferred_channel=args.channel,
        backend_name=args.backend,
        instance=args.instance,
        output_path=args.output,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["submitted_ok"]:
        raise SystemExit(2)
    final_status = report["job_status_final"]
    if final_status is not None and final_status not in PENDING_STATUSES and not report["result_available"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
