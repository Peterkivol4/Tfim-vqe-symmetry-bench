from __future__ import annotations

import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "fieldline_vqe" / "_native_kernels.c"
OUTDIR = ROOT / "src" / "fieldline_vqe"


def main() -> int:
    system = platform.system().lower()
    out = OUTDIR / ("_native_kernels.dylib" if system.startswith("darwin") else "_native_kernels.dll" if system.startswith("windows") else "_native_kernels.so")
    return subprocess.call(["gcc", "-O3", "-shared", "-fPIC", str(SRC), "-o", str(out)])


if __name__ == "__main__":
    raise SystemExit(main())
