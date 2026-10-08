-- Seed data for local development (fictitious)
INSERT INTO customers (id, full_name, email, phone, birth_date) VALUES
  (1, '⟪name:Lucas Morel⟫', '⟪email:lucas.morel@example.com⟫', '⟪phone:06 45 12 78 90⟫', '⟪birth_date:1990-05-17⟫'),
  (2, '⟪name:Amélie Rousseau⟫', '⟪email:amelie.rousseau@example.fr⟫', '⟪phone:07 12 34 98 76⟫', '⟪birth_date:1987-11-02⟫');

INSERT INTO api_keys (customer_id, api_key) VALUES (1, '⟪secret:sk_live_FAKEseedKEY00000⟫');

UPDATE settings SET value = '30' WHERE key = 'invoice_due_days';

CREATE TABLE customer_notes (customer_id INTEGER, author_name TEXT, body TEXT);
INSERT INTO customer_notes (customer_id, author_name, body) VALUES
  (1, 'support', 'Rappeler ⟪name:Hélène Garnier⟫ jeudi pour le devis.'),
  (2, 'support', 'Client absent, laisser un message à ⟪name:Mathis Roussel⟫.');
