import unittest

from privacy_guard.core.tabular import find_tabular_personal_data
from privacy_guard.core.tabular.fields import split_fields


def found(text):
    return [(f.kind, text[f.start:f.end]) for f in find_tabular_personal_data(text)]


class FieldsTest(unittest.TestCase):
    def test_quotes_protect_delimiters_and_are_not_part_of_the_value(self):
        text = "1, 'Dupont, Jean' , \"x\""

        values = [field.value(text) for field in split_fields(text, 0, len(text), ",")]

        self.assertEqual(values, ["1", "Dupont, Jean", "x"])


class CsvTablesTest(unittest.TestCase):
    def test_hides_personal_columns_of_every_row(self):
        text = "id;Prénom;Nom de famille;ville\n1;Lucas;Morel;Lyon\n2;Julie;Nguyen;Paris\n"

        self.assertEqual(found(text), [("person_name", "Lucas"), ("person_name", "Morel"),
                                       ("person_name", "Julie"), ("person_name", "Nguyen")])

    def test_ambiguous_name_column_needs_a_personal_neighbour(self):
        products = "id,name,price\n1,Widget,9.90\n"
        people = "id,name,email\n1,Lucas Morel,lm@example.com\n"

        self.assertEqual(found(products), [])
        self.assertEqual(found(people), [("person_name", "Lucas Morel")])

    def test_markdown_table_without_its_separator_line(self):
        text = "| Name | Email |\n|---|---|\n| Lucas Morel | lm@example.com |\n"

        self.assertEqual(found(text), [("person_name", "Lucas Morel")])

    def test_table_stops_at_a_blank_line(self):
        text = "first_name,last_name\nLucas,Morel\n\nWidget,Gadget\n"

        self.assertEqual(found(text), [("person_name", "Lucas"), ("person_name", "Morel")])


class SqlInsertsTest(unittest.TestCase):
    def test_hides_personal_values_of_every_row(self):
        text = ("INSERT INTO customers (id, full_name, birth_date, city) VALUES\n"
                "  (1, 'Lucas Morel', '1990-05-17', 'Lyon'),\n"
                "  (2, 'Jeanne d''Arc (test)', NULL, 'Paris');")

        self.assertEqual(found(text), [("person_name", "Lucas Morel"), ("birth_date", "1990-05-17"),
                                       ("person_name", "Jeanne d''Arc (test)")])

    def test_tables_without_personal_columns_are_left_alone(self):
        self.assertEqual(found("INSERT INTO settings (key, value) VALUES ('due_days', '30');"), [])


if __name__ == "__main__":
    unittest.main()
