"""Keep strict external placeholder literals, without exempting nearby values.

Only allowlisted uppercase labels plus a 3-6 digit counter are recognized.
Credential findings are never removed. Broad name spans are split at markers
so a marker cannot make an adjacent real name disappear from detection.
"""

import re

from privacy_guard.core.category_policy import Mode, mode_for
from privacy_guard.core.findings import Finding

_LABEL = r'(?:PERSON(?:_NAME)?|EMAIL|PHONE|ADDRESS|LOCATION|ORGANIZATION)_[0-9]{3,6}'
_MARKER = re.compile(rf'(?<!\w)(?:\[{_LABEL}\]|{_LABEL})(?!\w)')
_EDGE = " \t\r\n[](){}<>:;,.'\""


def preserve_markers(text: str, findings: list[Finding]) -> list[Finding]:
    if '_' not in text:
        return findings
    markers = [match.span() for match in _MARKER.finditer(text)]
    if not markers:
        return findings
    result = []
    for finding in findings:
        if mode_for(finding.kind) is Mode.REDACT:
            result.append(finding)
            continue
        overlaps = [(start, end) for start, end in markers
                    if start < finding.end and finding.start < end]
        if not overlaps:
            result.append(finding)
        elif finding.kind == 'person_name':
            cursor = finding.start
            for start, end in overlaps:
                _append_name(result, text, cursor, min(start, finding.end))
                cursor = max(cursor, end)
            _append_name(result, text, cursor, finding.end)
        elif not any(start <= finding.start and finding.end <= end for start, end in overlaps):
            # PERSON_001@example.org is a real mailbox-shaped value, not a marker.
            result.append(finding)
    return result


def _append_name(result, text, start, end):
    while start < end and text[start] in _EDGE:
        start += 1
    while end > start and text[end - 1] in _EDGE:
        end -= 1
    if start < end:
        result.append(Finding('person_name', start, end))
