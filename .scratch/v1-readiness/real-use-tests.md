# Real-use tests of 0.1.0-preview.4

Build: `dist/PrivacyGuard-0.1.0-preview.4-windows-x64.exe`, SHA-256
`aab2cc984c68704ed94b39ad3feaadf728b0c0dcbdc7e21b052eb578e267996f`.

Record each finding below with its date, what was done, what happened, and whether it
is blocking (leak, damaged file, work prevented) or V1.1. Never paste real personal
values here: describe them ("a client e-mail in a CSV").

## 1. Founder's machine, VS Code, normal work (several days)

Install: close every Claude Code session, run the setup over the development install
(it replaces the hooks), open a new session. Then check once:

- [ ] Start menu "Verifier Privacy Guard" succeeds.
- [ ] Reading a CSV or Markdown file with a name, an e-mail and a phone: tokens in the
      answer, one notification naming the document.
- [ ] Asking the agent to edit that file: the file on disk keeps the real values.
- [ ] Asking the agent to change a value in a `.py` file holding an e-mail: real
      e-mail on disk afterwards.
- [ ] Asking the agent to rewrite a `.env` holding a key: refused, key intact.
- [ ] `ls`, Glob and `git status` on a code project: no technical name masked.
- [ ] A failing command (`git push` without network, a missing file): the agent
      still sees a readable error.
- [ ] A subagent task and a long session with `/compact`: nothing unusual.

Then work normally and note anything that gets in the way.

## 2. Clean Windows account without Python

Windows 11 Home has no Sandbox or Hyper-V; Python is installed for the founder's
account only, so a new local account has none.

1. Settings > Accounts > Other users > Add account > "I don't have this person's
   sign-in information" > "Add a user without a Microsoft account".
2. Sign in to that account; check `python` is missing (`where python` finds only the
   Microsoft Store alias or nothing).
3. Install VS Code and the Claude Code extension; sign in and open it once.
4. Copy the setup to that account and run it with default options.
- [ ] Setup succeeds without Python, pip or any download.
- [ ] Same checks as section 1, first five boxes.
5. Uninstall from Installed apps: hooks removed, other Claude settings intact.
6. Delete the account afterwards (Settings > Accounts > Other users > Remove).

## Findings

| Date | Where | What happened | Blocking? | Follow-up |
| --- | --- | --- | --- | --- |
