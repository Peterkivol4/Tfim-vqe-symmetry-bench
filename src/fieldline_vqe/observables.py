from __future__ import annotations

import sys
from . import _observables_impl as _impl

__all__ = getattr(_impl, "__all__", [])
__doc__ = getattr(_impl, "__doc__", None)

sys.modules[__name__] = _impl
