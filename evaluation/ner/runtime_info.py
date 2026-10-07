"""Record process resource use and the actual evaluation runtime versions."""

import ctypes
import importlib.metadata
import platform


class ProcessMemory(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                *[(name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize",
                  "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                  "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]]


def peak_memory_bytes():
    info = ProcessMemory()
    info.cb = ctypes.sizeof(info)
    kernel, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(ProcessMemory), ctypes.c_ulong]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(info), info.cb):
        raise ctypes.WinError()
    return info.PeakWorkingSetSize


def versions():
    result = {"python": platform.python_version(), "os": platform.platform()}
    for name in ("numpy", "onnxruntime", "tokenizers", "torch", "gliner", "transformers"):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    return result
