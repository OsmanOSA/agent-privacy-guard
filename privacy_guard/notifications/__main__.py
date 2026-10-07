"""Detached worker entry point. No action without an explicit worker argument."""

import argparse


def main():
    from pathlib import Path
    from privacy_guard.notifications.worker import run_worker

    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["worker"])
    parser.add_argument("--directory", required=True, type=Path)
    args = parser.parse_args()
    return run_worker(args.directory.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
