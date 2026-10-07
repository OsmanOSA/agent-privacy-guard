"""Setup entry point and a small Windows status dialog; no terminal is required."""

import argparse
import ctypes
import sys
from pathlib import Path

from privacy_guard.setup.errors import user_message
from privacy_guard.setup.installation import install, preflight, status, uninstall


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['install', 'preflight', 'uninstall', 'status'])
    parser.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--user-home', type=Path, default=Path.home())
    parser.add_argument('--dialog', action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'status':
            version = status(args.user_home)
            message = (f'Privacy Guard {version}\n\nHooks Claude Code enregistrés et modèle local disponible.\n'
                       'Ouvrez une nouvelle session Claude Code pour utiliser cette installation.\n\n'
                       'Ce statut ne garantit pas la détection de toutes les données personnelles.')
        else:
            globals()[args.action](args.bundle.resolve(), args.user_home.resolve())
            message = 'Privacy Guard : operation terminée.'
        if args.dialog:
            ctypes.windll.user32.MessageBoxW(None, message, 'Privacy Guard', 0x40)
        elif sys.stdout:
            print(message)
        return 0
    except Exception as error:
        # The installer frames this text itself ("Installation incomplète. … Vos coffres
        # existants sont conservés."): stderr carries the French sentence only.
        if args.dialog:
            ctypes.windll.user32.MessageBoxW(None, f'Privacy Guard\n\n{user_message(error)}', 'Privacy Guard', 0x10)
        elif sys.stderr:
            print(user_message(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
