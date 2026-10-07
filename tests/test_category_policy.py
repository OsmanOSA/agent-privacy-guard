import unittest

from privacy_guard.core.category_policy import Mode, mode_for
from privacy_guard.core.personal_data_detector import PERSONAL_DATA_RULES
from privacy_guard.core.secret_detector import SECRET_RULES


class CategoryPolicyTest(unittest.TestCase):
    def test_every_secret_detector_kind_is_irreversible(self):
        for rule in SECRET_RULES:
            with self.subTest(kind=rule.kind):
                self.assertIs(mode_for(rule.kind), Mode.REDACT)

    def test_existing_personal_categories_keep_their_round_trip_except_card_codes(self):
        kinds = {rule.kind for rule in PERSONAL_DATA_RULES} | {"person_name", "postal_address"}
        for kind in kinds - {"card_security_code"}:
            with self.subTest(kind=kind):
                self.assertIs(mode_for(kind), Mode.PSEUDONYMIZE)

    def test_card_security_code_is_irreversible(self):
        self.assertIs(mode_for("card_security_code"), Mode.REDACT)

    def test_unknown_kind_defaults_to_irreversible_redaction(self):
        self.assertIs(mode_for("future_identifier"), Mode.REDACT)
