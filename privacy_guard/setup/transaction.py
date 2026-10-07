"""Rollback the specific files owned by setup; never snapshot session vaults."""

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from privacy_guard.setup.errors import SetupError


@contextmanager
def installation_transaction(home: Path, settings: Path):
    for target in (home, settings):
        for part in (target, *target.parents):
            if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
                raise SetupError('Le setup ne modifie pas un dossier redirigé (lien ou jonction).')
    home.mkdir(parents=True, exist_ok=True)
    lock = home / 'setup.lock'
    with lock.open('x', encoding='ascii') as stream:
        stream.write('installation in progress\n')
    targets = [home / name for name in (
        'app', 'models/distilcamembert-ner', 'ner-model.json', 'vault-format.json',
        'windows-setup.json', 'notifications/settings.json', 'data/insee-names.sqlite',
        'data/insee-names.source.json', 'data/INSEE-data-NOTICE.txt')]
    targets.append(settings)
    try:
        folder = tempfile.mkdtemp(prefix='setup-backup-', dir=home)
        try:
            saved = []
            for index, target in enumerate(targets):
                for part in (target, *target.parents):
                    if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
                        raise SetupError('Le setup ne modifie pas un fichier redirigé (lien).')
                backup = Path(folder) / str(index)
                exists = target.exists()
                if exists:
                    if target.is_dir():
                        shutil.copytree(target, backup)
                    else:
                        shutil.copyfile(target, backup)
                saved.append((target, backup, exists))
            try:
                yield
            except BaseException:
                for target, backup, existed in reversed(saved):
                    if target.is_dir():
                        shutil.rmtree(target)
                    elif target.exists():
                        target.unlink()
                    if existed:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if backup.is_dir():
                            shutil.copytree(backup, target)
                        else:
                            shutil.copyfile(backup, target)
                raise
        except BaseException:
            # Retain recovery bytes if rollback itself could not finish.
            raise
        else:
            shutil.rmtree(folder)
    finally:
        lock.unlink(missing_ok=True)
