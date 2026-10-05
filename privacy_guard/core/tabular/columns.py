"""Which columns hold personal data, from their names (French and English).

Interface: `personal_columns(column_names) -> {column index: finding kind}`.
"""

from __future__ import annotations

import re
import unicodedata

from privacy_guard.core.name_detector import PERSON_NAME

BIRTH_DATE = "birth_date"
POSTAL_ADDRESS = "postal_address"

_NAME_COLUMNS = {
    "fullname", "firstname", "lastname", "middlename", "surname", "givenname", "familyname",
    "prenom", "nomcomplet", "nomdefamille", "customername", "clientname", "contactname",
}
_BIRTH_DATE_COLUMNS = {"birthdate", "dateofbirth", "dob", "birthday", "datenaissance", "datedenaissance"}
_ADDRESS_COLUMNS = {"address", "streetaddress", "street", "addressline1", "addressline2", "adresse"}
# "name" alone is ambiguous: product names, project names... It counts as a
# person only next to a column that is clearly about a person.
_AMBIGUOUS_NAME_COLUMNS = {"name", "nom", "displayname"}
_CLEARLY_PERSONAL = (
    _NAME_COLUMNS | _BIRTH_DATE_COLUMNS | _ADDRESS_COLUMNS
    | {"email", "mail", "emailaddress", "phone", "phonenumber", "telephone", "mobile", "iban"}
)


def personal_columns(column_names: list[str]) -> dict[int, str]:
    """Maps the index of every personal column to the kind of finding its values are."""
    normalized = [normalize(name) for name in column_names]
    about_people = any(name in _CLEARLY_PERSONAL for name in normalized)
    kinds = {}
    for index, name in enumerate(normalized):
        if name in _NAME_COLUMNS or (about_people and name in _AMBIGUOUS_NAME_COLUMNS):
            kinds[index] = PERSON_NAME
        elif name in _BIRTH_DATE_COLUMNS:
            kinds[index] = BIRTH_DATE
        elif name in _ADDRESS_COLUMNS:
            kinds[index] = POSTAL_ADDRESS
    return kinds


def normalize(column_name: str) -> str:
    """Lower-case ASCII letters and digits only: "Date de naissance" -> "datedenaissance"."""
    without_accents = unicodedata.normalize("NFKD", column_name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", without_accents.lower())
