"""Personal data in tabular text: CSV-like tables and SQL INSERT statements.

A header or a column list names the columns; the values of personal columns are
hidden whatever they look like ("Morel" in a last_name column). Format-based
detectors cannot see them: a surname has no format.

Interface: `find_tabular_personal_data(text) -> list[Finding]`.
"""

from __future__ import annotations

from privacy_guard.core.findings import Finding, without_overlaps
from privacy_guard.core.tabular.csv_tables import find_in_csv_tables
from privacy_guard.core.tabular.sql_inserts import find_in_sql_inserts


def find_tabular_personal_data(text: str) -> list[Finding]:
    """Values of personal columns, in CSV-like tables and SQL INSERT statements."""
    return without_overlaps(find_in_csv_tables(text) + find_in_sql_inserts(text))
