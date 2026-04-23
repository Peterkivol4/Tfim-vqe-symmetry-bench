# Dependency inventory

## Runtime
- numpy==2.3.5 — numerical kernels for statevector, density-matrix, and measurement post-processing
- scipy==1.17.0 — eigensolvers, curve fitting, optimization helpers
- matplotlib==3.10.8 — local artifact rendering only
- qiskit==2.3.1 — circuit model and quantum-information primitives
- qiskit-aer==0.17.2 — local noisy simulation backend
- qiskit-algorithms==0.4.0 — optimizer integrations such as SPSA

## Optional runtime
- qiskit-ibm-runtime==0.46.1 — Runtime bridge; not required for local Aer workflows

## Development / audit
- pytest==8.4.1 — test runner
- pip-audit==2.9.0 — dependency CVE audit
- pip-licenses==5.0.0 — license inventory

## Native kernels
- gcc / clang toolchain — optional build-time requirement for the parity kernels in src/fieldline_vqe/_native_kernels.c
- the repo may also contain prebuilt platform-specific native parity libraries such as `src/fieldline_vqe/_native_kernels.so` or `src/fieldline_vqe/_native_kernels.dylib`
- those binaries are optional acceleration artifacts; the loader falls back to the pure-Python implementation if no compatible native library is present
- rebuild the native library for the current platform with `python tools_build_native.py` before packaging or redistribution
