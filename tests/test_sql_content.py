"""SQL restoration: data positions only, escaped for SQL."""

import unittest

from privacy_guard.exports.file_content import restore_text
from privacy_guard.exports.sql_content import restore_sql

NAME = "⟦PERSON_NAME:ABCDEF12⟧"
EMAIL = "⟦EMAIL:12345678⟧"
VALUES = {NAME: "Siobhan O'Brien", EMAIL: "siobhan@example.org"}


def restore(text):
    for token, value in VALUES.items():
        text = text.replace(token, value)
    return text


class SqlContentTest(unittest.TestCase):
    def test_literals_are_restored_with_doubled_quotes(self):
        sql = f"INSERT INTO customers (name, email) VALUES ('{NAME}', '{EMAIL}');\n"
        self.assertEqual(restore_sql(sql, restore),
                         "INSERT INTO customers (name, email) VALUES ('Siobhan O''Brien', 'siobhan@example.org');\n")

    def test_existing_escapes_in_a_literal_survive(self):
        sql = f"SELECT 'l''adresse de {NAME}';"
        self.assertEqual(restore_sql(sql, restore), "SELECT 'l''adresse de Siobhan O''Brien';")

    def test_tokens_outside_data_positions_stay_tokens(self):
        for sql in (f"SELECT * FROM t WHERE email = {EMAIL};", f'SELECT "{NAME}" FROM t;', f"SELECT `{NAME}` FROM t;"):
            with self.subTest(sql=sql):
                self.assertEqual(restore_sql(sql, restore), sql)

    def test_comments_are_restored_unless_the_value_could_end_them(self):
        sql = f"-- owner: {NAME}\n/* contact {EMAIL} */\nSELECT 1;\n"
        self.assertEqual(restore_sql(sql, restore),
                         "-- owner: Siobhan O'Brien\n/* contact siobhan@example.org */\nSELECT 1;\n")
        self.assertEqual(restore_sql(f"/* {NAME} */", lambda text: text.replace(NAME, "a */ b")), f"/* {NAME} */")
        self.assertEqual(restore_sql(f"-- {NAME}", lambda text: text.replace(NAME, "a\nDROP")), f"-- {NAME}")

    def test_quotes_inside_comments_and_identifiers_do_not_open_literals(self):
        sql = f"-- it's fine\nSELECT \"it's\" FROM t WHERE a = '{NAME}';"
        self.assertEqual(restore_sql(sql, restore), "-- it's fine\nSELECT \"it's\" FROM t WHERE a = 'Siobhan O''Brien';")

    def test_unterminated_regions_reject_the_content(self):
        for sql in (f"SELECT '{NAME};", 'SELECT "name;', f"/* {NAME}", "SELECT `name;"):
            with self.subTest(sql=sql):
                self.assertIsNone(restore_sql(sql, restore))

    def test_content_without_tokens_is_unchanged(self):
        sql = "INSERT INTO t VALUES ('a''b', \"c\"); -- note\n/* x */"
        self.assertEqual(restore_sql(sql, restore), sql)

    def test_format_dispatch(self):
        self.assertEqual(restore_text("seed.SQL", f"SELECT {NAME};", restore), f"SELECT {NAME};")
        self.assertEqual(restore_text("notes.md", f"{NAME}", restore), "Siobhan O'Brien")


if __name__ == "__main__":
    unittest.main()
