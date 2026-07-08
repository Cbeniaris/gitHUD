"""Repo list: name + path pairs, stored as JSON, one file per machine.

Deliberately not synced across machines -- paths like /mnt/drivename/unity/...
on Fedora don't map to anything sensible on macOS, so each machine maintains
its own list independently.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "githud"
CONFIG_FILE = CONFIG_DIR / "repos.json"


def load_repos() -> list[dict]:
    if not CONFIG_FILE.exists():
        return []
    try:
        return json.loads(CONFIG_FILE.read_text())
    except json.JSONDecodeError:
        return []


def save_repos(repos: list[dict]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(repos, indent=2))


def add_repo(name: str, path: str) -> None:
    repos = load_repos()
    resolved = str(Path(path).expanduser().resolve())
    repos = [r for r in repos if r["path"] != resolved]  # avoid duplicate paths
    repos.append({"name": name, "path": resolved})
    save_repos(repos)


def remove_repo(path: str) -> None:
    repos = load_repos()
    resolved = str(Path(path).expanduser().resolve())
    repos = [r for r in repos if r["path"] != resolved]
    save_repos(repos)
