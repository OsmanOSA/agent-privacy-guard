# Notes de session Claude Code

Claude Code lit les fichiers avec l'outil Read, les modifie avec Edit ou Write
et cherche avec Grep et Glob. Les commandes passent par Bash ou PowerShell.
Claude propose ensuite un plan ; Claude Code l'applique après validation.

| Outil | Rôle |
| --- | --- |
| `Read` | lit un fichier |
| `Write` | écrit un fichier |
| `Bash` | lance une commande |
| `Grep` | cherche un motif |

Vérifier la version avec `claude --version`, puis relancer claude code.

```python
def read(path):
    with open(path) as handle:
        return handle.read()

code = read("notes.md")
write = print
```

Revue faite avec ⟪name:Claude Moreau⟫ (équipe data), joignable à
⟪email:claude.moreau@exemple-studio.fr⟫. ⟪name:Moreau⟫ valide le plan vendredi.
