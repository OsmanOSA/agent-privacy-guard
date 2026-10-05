"""French postal addresses, recognised without an NLP model.

An address is a street line, optionally followed by a postal code and a city,
on the same line or the next one (letter layout):

    12 bis rue de l'Église, 75002 Paris
    45 boulevard Haussmann
    75009 PARIS CEDEX 09

The street line needs a number, a street type and a capitalised street name:
"rue" alone ("dans la rue", "3 rues") is ordinary text. Addresses written all
in lowercase are missed: that is the price of keeping false positives low
without a language model.
"""

from __future__ import annotations

from privacy_guard.core.pattern_rule import NUMBER_START, rule

_STREET_TYPES = (
    "rue|avenue|av\\.|boulevard|bd|all[ée]e|chemin|impasse|place|quai|route|cours|square|passage|"
    "sentier|voie|r[ée]sidence|lotissement|hameau|faubourg|fbg|esplanade|promenade|rond-point|"
    "cit[ée]|villa|parvis|traverse|mont[ée]e|chauss[ée]e|ruelle|mail|clos|lieu-dit"
)
# Small words allowed inside a street or city name: "rue de la Paix", "place Saint-Germain-des-Prés".
_PARTICLE = r"(?:de|du|des|la|le|les|à|au|aux|en|sur|sous|et|st\.|ste\.)"
# A name word starts with a capital or a digit ("8 Mai 1945"), possibly after an elision ("l'Église").
_NAME_WORD = r"(?:[ldLD]['’])?[A-ZÀ-ÖØ-Ý0-9][\w'’-]*"
_SPACE = r"[ \t]"

_STREET_NAME = (
    rf"(?:{_PARTICLE}[ \t-]+)*{_NAME_WORD}"
    rf"(?:[ \t-]+(?:{_PARTICLE}[ \t-]+)*{_NAME_WORD}){{0,5}}"
)
_STREET_LINE = (
    NUMBER_START
    + rf"\d{{1,4}}(?:{_SPACE}?(?:bis|ter|quater|[A-D]))?{_SPACE}*,?{_SPACE}+"
    + rf"(?i:{_STREET_TYPES}){_SPACE}+{_STREET_NAME}"
)
# Optional ", 75002 Paris", possibly on the next line, with an optional CEDEX.
_POSTAL_LINE = (
    rf"(?:{_SPACE}*,)?{_SPACE}*\n?{_SPACE}*\d{{5}}{_SPACE}+"
    rf"{_NAME_WORD}(?:[ \t-]+{_NAME_WORD}){{0,3}}(?:{_SPACE}+CEDEX(?:{_SPACE}+\d{{1,2}})?)?"
)

FRENCH_ADDRESS_RULE = rule("fr_postal_address", rf"{_STREET_LINE}(?:{_POSTAL_LINE})?")
