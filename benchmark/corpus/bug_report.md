## Bug: PDF export fails for invoices with accented customer names

**Reported by:** ⟪name:Sophie Lefèvre⟫ (⟪email:sophie.lefevre@example.com⟫)
**Version:** 2.4.1 on Windows 11, Python 3.12.4

### Steps to reproduce

1. Create a customer named "⟪name:Éloïse Dubois-Lambert⟫"
2. Generate an invoice and click **Export PDF**

### Expected

A PDF showing the customer name.

### Actual

```
UnicodeEncodeError: 'charmap' codec can't encode character 'É' in position 12
  File "invoice_forge/render.py", line 88, in render_invoice
```

### Notes

Works on macOS. @rmehta suggested forcing UTF-8 in `render.py`. Possibly related to #142.
Card used for the test payment: ⟪banking:4111 1111 1111 1111⟫, CVV ⟪banking:737⟫.
