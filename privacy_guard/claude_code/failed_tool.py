"""Stop on sensitive failed-tool errors: this event cannot replace their text."""

from privacy_guard.claude_code.responses import HookResult, allow, stop
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.diagnostics import record_failure

ERROR_NOTICE = (
    "Privacy Guard : données détectées dans un message d’erreur non remplaçable. "
    "Traitement interrompu. Ne reprenez pas cette session avant d’avoir vérifié son contenu."
)


def protect_failed_tool(payload: dict, core: PrivacyCore, failures=None) -> HookResult:
    error = payload.get("error")
    if not isinstance(error, str):
        record_failure(failures, 'PostToolUseFailure', payload.get('tool_name'),
                       at='failed_tool', category='unsupported_schema')
        return stop("Privacy Guard : format d’erreur inconnu, traitement interrompu.")
    # additionalContext cannot replace the original error. Do not echo either
    # version: the universal stop prevents the next automatic model request.
    if core.protect(error) == error:
        return allow()
    record_failure(failures, 'PostToolUseFailure', payload.get('tool_name'),
                   at='failed_tool', category='sensitive_result')
    return stop(ERROR_NOTICE)
