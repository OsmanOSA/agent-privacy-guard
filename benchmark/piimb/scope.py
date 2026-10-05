"""Which PIIMB labels Privacy Guard is meant to hide (PRD §24).

PIIMB counts 103 labels as PII, including ordinary dates, cities, companies,
occupations or gender, which Privacy Guard deliberately leaves visible: the
agent needs them to work. Recall restricted to these labels measures the
product on what it claims to do; the official score measures it on PIIMB's terms.
"""

from __future__ import annotations

PRODUCT_SCOPE = {
    "name": {"GIVENNAME", "SURNAME", "PERSON", "first_name", "last_name", "name"},
    "email": {"EMAIL", "EMAIL_ADDRESS", "email"},
    "phone": {"PHONE_NUMBER", "TELEPHONENUM", "phone_number", "fax_number"},
    "address": {"STREET", "BUILDINGNUM", "street_address", "address"},
    "birth_date": {"date_of_birth"},
    "identifier": {"SOCIALNUM", "ssn", "US_SSN", "national_id", "PASSPORTNUM", "US_PASSPORT", "IDCARDNUM",
                   "DRIVERLICENSENUM", "US_DRIVER_LICENSE", "TAXNUM", "tax_id", "US_ITIN", "license_plate",
                   "US_LICENSE_PLATE"},
    "banking": {"CREDITCARDNUMBER", "CREDIT_CARD", "credit_card_number", "credit_debit_card", "IBAN_CODE",
                "cvv", "account_number", "US_BANK_NUMBER"},
    "secret": {"PASSWORD", "password", "api_key"},
}
_CATEGORY_OF_LABEL = {label: category for category, labels in PRODUCT_SCOPE.items() for label in labels}


def scope_category(label: str) -> str | None:
    """The product category of a PIIMB label, or None when it is out of scope by design."""
    return _CATEGORY_OF_LABEL.get(label)
