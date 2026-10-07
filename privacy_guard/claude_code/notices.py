"""Content-free user notices through Claude Code's native systemMessage field."""

import json

from privacy_guard.claude_code.responses import HookResult

PROTECTED_NOTICE = "Privacy Guard : données détectées pseudonymisées ou masquées dans le résultat."
RESTORED_NOTICE = "Privacy Guard : données personnelles restituées dans le fichier local."
RESTORE_FAILED_NOTICE = "Privacy Guard : restitution locale impossible. Vérifiez le fichier avant de l’utiliser."


def notify(result: HookResult, message: str) -> HookResult:
    response = json.loads(result.stdout) if result.stdout else {}
    response["systemMessage"] = message
    return HookResult(result.exit_code, json.dumps(response, ensure_ascii=False), result.stderr)
