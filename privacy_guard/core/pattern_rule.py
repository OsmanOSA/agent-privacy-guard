"""Pattern rules: one kind of sensitive value, the regex that finds it, and an optional check.

Shared by every detector. The optional validator (a checksum such as Luhn or
mod 97) rejects look-alike numbers: that is what keeps false positives low.

Interface: `rule(kind, regex, is_valid)` to declare, `find_with(rules, text)` to run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator

from privacy_guard.core.findings import Finding, without_overlaps

# When a pattern defines this group, only the group is sensitive, not the whole match.
VALUE_GROUP = "value"

# A word character or a "+" right before or after means we are inside a longer
# token (timestamp, identifier, hash): not a standalone number. Neither are the
# digits of a decimal: 0.5123456789012345 is a score, not a card number.
NUMBER_START = r"(?<![\w+])(?<!\d[.,])"
NUMBER_END = r"(?!\w)(?![.,]\d)"


@dataclass(frozen=True)
class PatternRule:
    """One kind of sensitive value and how to recognise it."""

    kind: str
    pattern: re.Pattern
    is_valid: Callable[[str], bool] | None = None

    def find(self, text: str) -> Iterator[Finding]:
        """Yields every occurrence that passes the validator, if there is one."""
        group = VALUE_GROUP if VALUE_GROUP in self.pattern.groupindex else 0
        for match in self.pattern.finditer(text):
            if self.is_valid is None or self.is_valid(match.group(group)):
                yield Finding(self.kind, match.start(group), match.end(group))


def rule(kind: str,
         regex: str,
         is_valid: Callable[[str], bool] | None = None) -> PatternRule:
    """Declares a rule from a regex string."""
    return PatternRule(kind, re.compile(regex), is_valid)


def labelled_rule(kind: str,
                  label: str,
                  value: str,
                  is_valid: Callable[[str], bool] | None = None) -> PatternRule:
    """Declares a rule for a value that is only recognisable by the label before it.

    Matches e.g. "SIRET : 123...", "N° CNI 123...", "Permis de conduire n° 123...".
    The label is case-insensitive; only the value is reported.
    """
    regex = (
        rf"(?i:\b(?:{label})(?:\s+(?:n°|no\.?|num[ée]ro|number))?)"
        rf"\s*[:#=-]?\s*(?P<{VALUE_GROUP}>{value}){NUMBER_END}"
    )
    return rule(kind, regex, is_valid)


def find_with(rules: Iterable[PatternRule],
              text: str) -> list[Finding]:
    """Runs every rule and returns ordered, non-overlapping findings.

    On a full tie, the rule listed first wins: list the most specific rules first.
    """
    return without_overlaps(finding for each_rule in rules for finding in each_rule.find(text))
