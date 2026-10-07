"""Fetch pinned public corpora and verify every file against sources.json."""

import hashlib
from pathlib import Path
from urllib.request import Request, urlopen

from .license_policy import eligible_datasets

BASE = Path(__file__).resolve().parent


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def fetch_file(asset):
    target = BASE / "data" / "raw" / asset["local_path"]
    if target.exists() and sha256(target.read_bytes()) == asset["sha256"]:
        return
    request = Request(asset["url"], headers={"User-Agent": "PrivacyGuardNERResearch/1.0"})
    with urlopen(request, timeout=45) as response:
        data = response.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024 or sha256(data) != asset["sha256"]:
        raise ValueError(f"Unexpected dataset bytes: {asset['local_path']}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".download")
    temporary.write_bytes(data)
    temporary.replace(target)


def main():
    for dataset in eligible_datasets():
        for asset in dataset["assets"]:
            fetch_file(asset)
        print(f"Verified {dataset['id']}")


if __name__ == "__main__":
    main()
