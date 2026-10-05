# invoice-forge

[![CI](https://github.com/acme-labs/invoice-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/acme-labs/invoice-forge/actions)

Generate PDF invoices from JSON. Built with FastAPI, Jinja2 and WeasyPrint.

## Quick start

```bash
pip install invoice-forge
export INVOICE_FORGE_API_KEY=⟪secret:ifk_live_8f3K2pQ9xLm4Rt7Vb1Nc6Ws0⟫
invoice-forge serve --port 8080
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `INVOICE_FORGE_PORT` | `8080` | HTTP port |
| `INVOICE_FORGE_LOG_LEVEL` | `info` | Log verbosity |
| `INVOICE_FORGE_TEMPLATE_DIR` | `./templates` | Jinja2 templates |

## Contributing

Pull requests are welcome. Read CONTRIBUTING.md and run `make test` before submitting.
Questions go to GitHub Discussions, not to the issue tracker.

## Maintainers

- ⟪name:Camille Fontaine⟫ (@cfontaine) - ⟪email:camille.fontaine@example.org⟫
- ⟪name:Rahul Mehta⟫ (@rmehta)

## Acknowledgements

Thanks to the WeasyPrint team and to Kozea for their support. Logo by ⟪name:Inès Barbier⟫.

## License

MIT © 2026 Acme Labs
