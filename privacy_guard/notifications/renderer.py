"""Select presentation independently of grouping, origin and protection."""

from privacy_guard.notifications.config import read_style


def create_renderer(directory):
    if read_style(directory) == "card":
        from privacy_guard.notifications.windows_card import WindowsCard
        return WindowsCard(directory)
    from privacy_guard.notifications.windows_banner import WindowsBanner
    return WindowsBanner()
