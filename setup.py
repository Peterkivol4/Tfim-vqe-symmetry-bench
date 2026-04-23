from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src" / "fieldline_vqe" / "_native_kernels.c"
OUTDIR = ROOT / "src" / "fieldline_vqe"


class build_py(_build_py):
    def run(self):
        system = platform.system().lower()
        out = OUTDIR / ("_native_kernels.dylib" if system.startswith("darwin") else "_native_kernels.dll" if system.startswith("windows") else "_native_kernels.so")
        try:
            subprocess.check_call(["gcc", "-O3", "-shared", "-fPIC", str(SRC), "-o", str(out)])
        except Exception:
            pass
        super().run()


setup(cmdclass={"build_py": build_py})
