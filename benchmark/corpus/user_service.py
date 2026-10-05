"""User service: creates and looks up users.

Author: ⟪name:Rahul Mehta⟫ <⟪email:rahul.mehta@example.net⟫>
"""

from dataclasses import dataclass

DEFAULT_PAGE_SIZE = 50
PASSWORD_MIN_LENGTH = 12
API_KEY_HEADER = "X-Api-Key"
TOKEN_TTL_SECONDS = 3600


@dataclass
class User:
    name: str
    email: str


def test_create_user(client):
    user = client.create_user(User(name="⟪name:Alice Martin⟫", email="⟪email:alice.martin@example.com⟫"))
    assert user.id > 0


def notify_admin(mailer):
    # TODO(⟪name:Camille Fontaine⟫): move the address to settings
    mailer.send("⟪email:admin@acme-labs.example⟫", subject="New user")
