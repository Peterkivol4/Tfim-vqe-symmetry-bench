from __future__ import annotations

import ctypes
import os
from typing import Iterable

__all__ = ["SecureBuffer"]


class SecureBuffer:
    def __init__(self, payload: bytes | bytearray | memoryview | Iterable[int]) -> None:
        data = bytes(payload)
        self._size = len(data)
        self._buf = ctypes.create_string_buffer(self._size)
        if self._size:
            ctypes.memmove(self._buf, data, self._size)
        self._locked = False
        self._try_mlock()

    def _try_mlock(self) -> None:
        if os.name != "posix" or self._size == 0:
            return
        try:
            libc = ctypes.CDLL(None)
            if libc.mlock(ctypes.c_void_p(ctypes.addressof(self._buf)), ctypes.c_size_t(self._size)) == 0:
                self._locked = True
        except Exception:
            self._locked = False

    def _try_munlock(self) -> None:
        if not self._locked or os.name != "posix" or self._size == 0:
            return
        try:
            libc = ctypes.CDLL(None)
            libc.munlock(ctypes.c_void_p(ctypes.addressof(self._buf)), ctypes.c_size_t(self._size))
        except Exception:
            pass
        finally:
            self._locked = False

    def __len__(self) -> int:
        return self._size

    def __repr__(self) -> str:
        return "[REDACTED]"

    __str__ = __repr__

    def __bytes__(self) -> bytes:
        return ctypes.string_at(self._buf, self._size)

    def close(self) -> None:
        if getattr(self, "_buf", None) is None:
            return
        if self._size:
            ctypes.memset(self._buf, 0, self._size)
        self._try_munlock()
        self._buf = None
        self._size = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __reduce_ex__(self, protocol):
        raise TypeError("SecureBuffer cannot be pickled")

    def __copy__(self):
        raise TypeError("SecureBuffer cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("SecureBuffer cannot be copied")

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
