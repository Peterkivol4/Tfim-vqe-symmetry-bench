from __future__ import annotations

from typing import Mapping

from ._native_bridge import sector_mask, weighted_parity

__all__ = ["parity_expectation", "SymmetryGate"]


def _clean_counts(counts: Mapping[str, float]):
    keys = []
    vals = []
    odd_flags = []
    for bitstring, value in counts.items():
        cleaned = bitstring.replace(" ", "")
        keys.append(cleaned)
        vals.append(float(value))
        odd_flags.append(cleaned.count("1") % 2)
    return keys, vals, odd_flags


def parity_expectation(counts: Mapping[str, float]) -> float:
    _, vals, odd_flags = _clean_counts(counts)
    return weighted_parity(odd_flags, vals)


class SymmetryGate:
    @staticmethod
    def filter_by_x_parity(counts: Mapping[str, float], sector: int = 1) -> dict[str, float]:
        keys, vals, odd_flags = _clean_counts(counts)
        keep = sector_mask(odd_flags, want_even=int(sector) >= 0)
        return {key: val for key, val, mask in zip(keys, vals, keep) if mask}

    @staticmethod
    def filter_even_parity(counts: Mapping[str, float]) -> dict[str, float]:
        return SymmetryGate.filter_by_x_parity(counts, sector=1)
