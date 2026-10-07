"""Suspend and resume a profile's name service, to stall the detector (Windows only).

A suspended process keeps its pipe open but never answers, like a detector stuck on a
saturated machine: the hook must still answer before Claude Code's timeout.

Interface:
    pids = service_pids(profile_root)
    suspend(pids) / resume(pids)
"""

from __future__ import annotations

import ctypes
import json
import subprocess
from pathlib import Path

_PROCESS_SUSPEND_RESUME = 0x0800


def service_pids(profile_root: Path) -> list[int]:
    """Name-service processes whose command line points inside this profile."""
    # Filtering on python.exe keeps out this query's own PowerShell process.
    script = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
              "Where-Object { $_.CommandLine -like '*privacy_guard.service*' "
              f"-and $_.CommandLine -like '*{profile_root}*' }} | Select-Object -ExpandProperty ProcessId "
              "| ConvertTo-Json -Compress")
    output = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script],
                            capture_output=True, text=True, timeout=60).stdout.strip()
    found = json.loads(output) if output else []
    return found if isinstance(found, list) else [found]


def suspend(pids: list[int]) -> None:
    _each(pids, "NtSuspendProcess")


def resume(pids: list[int]) -> None:
    _each(pids, "NtResumeProcess", missing_ok=True)


def _each(pids: list[int], call: str, missing_ok: bool = False) -> None:
    kernel, ntdll = ctypes.windll.kernel32, ctypes.windll.ntdll
    for pid in pids:
        handle = kernel.OpenProcess(_PROCESS_SUSPEND_RESUME, False, pid)
        if not handle:
            if missing_ok:
                continue  # Stopped meanwhile, e.g. by the uninstaller.
            raise OSError(f"Cannot open name service process {pid}")
        try:
            getattr(ntdll, call)(handle)
        finally:
            kernel.CloseHandle(handle)
