import unittest
from pathlib import Path

from privacy_guard.core.secret_detector import find_secrets
from tests.fakes import STRIPE_KEY

PLAYGROUND = Path(__file__).resolve().parent.parent / "playground"

# Every secret of playground/.env, exactly as it must be cut out.
PLAYGROUND_SECRETS = {
    "FakePassw0rd123",
    "FakeRedisPass456",
    STRIPE_KEY,
    "sk-proj-FAKEFAKEFAKE0000000000000000000000000000",
    "sk-ant-api03-FAKEFAKEFAKE00000000000000000000000000000000",
    "AKIAIOSFODNN7EXAMPLE",
    "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "ghp_FAKEFAKEFAKE000000000000000000000000",
    "fake-jwt-signing-secret-do-not-use-0000",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ"
    ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
}


def detected(text):
    return {text[finding.start:finding.end] for finding in find_secrets(text)}


class PlaygroundEnvTest(unittest.TestCase):
    def setUp(self):
        self.env = (PLAYGROUND / ".env").read_text(encoding="utf-8")

    def test_detects_every_secret_and_nothing_else(self):
        self.assertEqual(detected(self.env), PLAYGROUND_SECRETS)

    def test_leaves_non_sensitive_values_alone(self):
        found = " ".join(detected(self.env))

        for value in ("acme-shop", "development", "3000", "debug", "jean.dupont@example.com"):
            self.assertNotIn(value, found)

    def test_finds_nothing_in_env_example(self):
        example = (PLAYGROUND / ".env.example").read_text(encoding="utf-8")

        self.assertEqual(find_secrets(example), [])


class RuleTest(unittest.TestCase):
    def test_url_keeps_everything_but_the_password(self):
        self.assertEqual(detected("postgres://admin:s3cret@db.example.com:5432/app"), {"s3cret"})

    def test_url_with_port_only_is_not_a_secret(self):
        self.assertEqual(detected("https://example.com:8080/path"), set())

    def test_stripe_publishable_key_is_public(self):
        self.assertEqual(detected("pk_live_FAKEFAKEFAKE00000000000000"), set())

    def test_detects_private_key_block(self):
        key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEfake\n-----END RSA PRIVATE KEY-----"

        self.assertEqual(detected(f"before\n{key}\nafter"), {key})

    def test_reports_most_specific_kind_on_overlap(self):
        findings = find_secrets("GITHUB_TOKEN=ghp_FAKEFAKEFAKE000000000000000000000000")

        self.assertEqual([finding.kind for finding in findings], ["github_token"])

    def test_ignores_code_reading_a_secret_from_the_environment(self):
        self.assertEqual(detected('password = os.environ["DB_PASSWORD"]'), set())
        self.assertEqual(detected('API_KEY = os.environ["API_KEY"]'), set())
        self.assertEqual(detected("DB_PASSWORD=${VAULT_DB_PASSWORD}"), set())

    def test_ignores_constants_that_are_not_secrets(self):
        self.assertEqual(detected("PASSWORD_MIN_LENGTH = 8"), set())
        self.assertEqual(detected('TOKEN_OPENING = "⟦"'), set())

    def test_detects_secret_literal_in_code(self):
        self.assertEqual(detected('SECRET_KEY = "django-insecure-abc123xyz"'), {"django-insecure-abc123xyz"})


class SecretAssignmentTest(unittest.TestCase):
    def test_detects_secrets_in_any_casing_and_place(self):
        for text, secret in (
            ("  password: Mailer-Secret-2026", "Mailer-Secret-2026"),
            ('{"api_key": "abcd1234efgh"}', "abcd1234efgh"),
            ("SMTP user=bob password=Smtp-Pass-2026! retrying", "Smtp-Pass-2026!"),
            ("https://api.example.com/v1?token=a1b2c3d4e5f6", "a1b2c3d4e5f6"),
            ("Mot de passe : Lyon-2026-secret", "Lyon-2026-secret"),
        ):
            self.assertEqual(detected(text), {secret}, text)

    def test_ignores_settings_that_name_a_secret_without_holding_one(self):
        for text in ('API_KEY_HEADER = "X-Api-Key"', "TOKEN_TTL_SECONDS = 3600", "max_tokens=4096",
                     "db.connect(password=PASSWORD)", "token: ${{ secrets.GITHUB_TOKEN }}", "password: str"):
            self.assertEqual(detected(text), set(), text)


if __name__ == "__main__":
    unittest.main()
