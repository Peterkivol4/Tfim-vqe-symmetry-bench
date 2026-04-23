from __future__ import annotations

import sys
from . import _cli_impl as _impl

__all__ = getattr(_impl, "__all__", [])
__doc__ = getattr(_impl, "__doc__", None)

if __name__ == "__main__":
    _impl.main()
else:
    sys.modules[__name__] = _impl
