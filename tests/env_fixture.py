"""Synthetic environment data: tests never read a developer's local .env."""

from tests.fakes import STRIPE_KEY

SYNTHETIC_ENV = "\n".join([
    "APP_NAME=acme-shop", "APP_ENV=development", "PORT=3000", "LOG_LEVEL=debug",
    "CONTACT_EMAIL=jean.dupont@example.com", "CONTACT_PHONE=+33 6 12 34 56 78",
    "DATABASE_URL=postgres://admin:FakePassw0rd123@db.example.com:5432/app",
    "REDIS_URL=redis://:FakeRedisPass456@redis.example.com:6379/0",
    "STRIPE_SECRET_KEY=" + STRIPE_KEY,
    "OPENAI_API_KEY=" + "sk-proj-" + "FAKEFAKEFAKE0000000000000000000000000000",
    "ANTHROPIC_API_KEY=" + "sk-ant-api03-" + "FAKEFAKEFAKE00000000000000000000000000000000",
    "AWS_ACCESS_KEY_ID=" + "AKIA" + "IOSFODNN7EXAMPLE",
    "AWS_SECRET_ACCESS_KEY=" + "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "GITHUB_TOKEN=" + "ghp_" + "FAKEFAKEFAKE000000000000000000000000",
    "JWT_SECRET=fake-jwt-signing-secret-do-not-use-0000",
    "SESSION_TOKEN=" + "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ"
    ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
])
