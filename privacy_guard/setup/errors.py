"""Setup failures carrying the French text the installer shows.

The installer speaks French (packaging/windows/setup.nsi). It used to show the raw
English exception text inside its French frame. A SetupError carries the sentence
meant for the user; any other error shows a fixed category only, never its text,
which can contain paths and therefore the Windows user name.

Interface: SetupError(message), user_message(error) -> str
"""

from privacy_guard.diagnostics import failure_details

DOWNLOAD_AGAIN = "téléchargez à nouveau le setup de Privacy Guard."


class SetupError(RuntimeError):
    """A failure the user can understand and act on."""


def user_message(error: Exception) -> str:
    if isinstance(error, SetupError):
        return str(error)
    _, category = failure_details(error)
    return f"Erreur inattendue ({category}). Relancez l’installation ; si elle échoue encore, {DOWNLOAD_AGAIN}"
