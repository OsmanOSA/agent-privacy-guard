# Playground

A fake project used to watch Privacy Guard work inside a real Claude Code session.
**Every secret and every piece of personal data here is fake.**

## Files

- `.env`: three groups of values.
  - Not sensitive (`APP_NAME`, `PORT`...): must reach the model unchanged.
  - Secrets (database URLs, API keys, tokens): must never reach the model.
  - Personal data (email, phone): must be pseudonymized.
- `.env.example`: the same keys without values, as a real project would ship.
- `fiche_client.txt`: a French customer record (phone, email, social security
  number, tax number, passport, plate, IBAN, card). Order number, date, amount
  and file reference are traps: they must stay visible. Name and postal address
  are not detected yet (they need a local NLP model).

## Manual scenario

1. Open a Claude Code session in this folder.
2. Ask: *"Check my .env and tell me which services this app uses."*
3. Look at what the model quotes back:
   - **Without protection**: it can repeat the keys verbatim.
   - **With protection** (goal): it sees placeholders such as `⟦SECRET:…⟧`, still understands which services are configured, and the real values stay on the machine.
4. Check `~/.privacy-guard/logs/guard.log`: it lists events, never values.
