"""Pure host-window selection and delivery decisions, without desktop access."""

HOSTS = {"code.exe": "vscode", "code - insiders.exe": "vscode",
         "windowsterminal.exe": "terminal", "conhost.exe": "terminal",
         "powershell.exe": "terminal", "pwsh.exe": "terminal", "cmd.exe": "terminal",
         "claude.exe": "claude"}


def choose_origin(pid, processes, windows):
    seen = set()
    for _ in range(32):
        if pid in seen or pid not in processes:
            break
        seen.add(pid)
        parent, executable = processes[pid]
        host = HOSTS.get(executable.lower())
        candidates = windows.get(pid, [])
        if host and candidates:
            # Multiple editor windows cannot be resolved from a process ID.
            return (pid, candidates[0], host) if len(candidates) == 1 else None
        pid = parent
    return None


def delivery_policy(mode, origin, foreground, owner):
    if mode == "off":
        return "off"
    if mode == "always":
        return "send_always"
    if not origin or owner != (origin["pid"], origin["created"]):
        return "send_unknown"
    return "suppress_foreground" if foreground == origin["hwnd"] else "send_background"
