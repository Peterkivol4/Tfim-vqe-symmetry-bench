from __future__ import annotations

import ctypes
import os
import platform
from pathlib import Path

__all__ = ["native_available", "weighted_parity", "sector_mask"]


def _load_native():
    if os.getenv("FIELDLINE_DISABLE_NATIVE", "0") == "1":
        return None
    here = Path(__file__).resolve().parent
    system = platform.system().lower()
    suffixes = {
        "darwin": [".dylib", ".so", ".dll"],
        "windows": [".dll", ".so", ".dylib"],
    }.get(system, [".so", ".dylib", ".dll"])
    for suffix in suffixes:
        candidate = here / f"_native_kernels{suffix}"
        if candidate.exists():
            try:
                lib = ctypes.CDLL(str(candidate))
            except OSError:
                continue
            lib.weighted_parity.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_double), ctypes.c_size_t]
            lib.weighted_parity.restype = ctypes.c_double
            lib.sector_mask.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t, ctypes.c_int]
            return lib
    return None


_lib = _load_native()
native_available = _lib is not None


def weighted_parity(odd_flags, weights):
    if not native_available:
        total = float(sum(weights))
        if total <= 0.0:
            return 0.0
        signed = sum((-float(w) if int(flag) else float(w)) for flag, w in zip(odd_flags, weights))
        return float(signed / total)
    n = len(weights)
    flags_arr = (ctypes.c_ubyte * n)(*[1 if int(flag) else 0 for flag in odd_flags])
    vals_arr = (ctypes.c_double * n)(*[float(w) for w in weights])
    return float(_lib.weighted_parity(flags_arr, vals_arr, n))


def sector_mask(odd_flags, want_even: bool):
    if not native_available:
        return [1 if (int(flag) == 0) == bool(want_even) else 0 for flag in odd_flags]
    n = len(odd_flags)
    flags_arr = (ctypes.c_ubyte * n)(*[1 if int(flag) else 0 for flag in odd_flags])
    out_arr = (ctypes.c_ubyte * n)()
    _lib.sector_mask(flags_arr, out_arr, n, 1 if want_even else 0)
    return [int(out_arr[i]) for i in range(n)]
