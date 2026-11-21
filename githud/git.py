"""Thin wrapper around the git CLI. Every function shells out to the real
`git` binary -- no git library, no reimplemented plumbing. This is what
keeps the whole tool ~identical on Fedora and macOS: same git binary,
same behavior.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(Exception):
    pass


def _run(repo_path: str, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", repo_path] + args,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def is_repo(path: str) -> bool:
    return (Path(path).expanduser() / ".git").exists()


def current_branch(repo_path: str) -> str:
    try:
        return _run(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"]).strip()
    except GitError:
        return "?"


def is_dirty(repo_path: str) -> bool:
    try:
        return bool(_run(repo_path, ["status", "--porcelain"]).strip())
    except GitError:
        return False


def status(repo_path: str) -> list[tuple[str, str]]:
    """Return list of (status_code, filepath) from porcelain output."""
    out = _run(repo_path, ["status", "--porcelain"])
    entries = []
    for line in out.splitlines():
        if not line.strip():
            continue
        entries.append((line[:2], line[3:]))
    return entries


def diff(repo_path: str, path: str | None = None) -> str:
    args = ["diff", "HEAD", "--"] if path is None else ["diff", "HEAD", "--", path]
    try:
        out = _run(repo_path, args)
        return out if out.strip() else "(no changes)"
    except GitError as e:
        return str(e)


def log(repo_path: str, n: int = 50) -> str:
    try:
        return _run(repo_path, ["log", f"-n{n}", "--oneline", "--graph", "--decorate"])
    except GitError as e:
        return str(e)


def stage(repo_path: str, path: str) -> None:
    _run(repo_path, ["add", "--", path])


def unstage(repo_path: str, path: str) -> None:
    _run(repo_path, ["restore", "--staged", "--", path])


def stage_all(repo_path: str) -> None:
    _run(repo_path, ["add", "."])


def commit(repo_path: str, message: str) -> str:
    return _run(repo_path, ["commit", "-m", message])


def push(repo_path: str) -> str:
    return _run(repo_path, ["push"])


def pull(repo_path: str) -> str:
    return _run(repo_path, ["pull"])


def has_remote(repo_path: str, name: str) -> bool:
    try:
        _run(repo_path, ["remote", "get-url", name])
        return True
    except GitError:
        return False


def set_origin(repo_path: str, url: str) -> None:
    if has_remote(repo_path, "origin"):
        _run(repo_path, ["remote", "set-url", "origin", url])  # origin exists, so update it
    else:
        _run(repo_path, ["remote", "add", "origin", url])


def set_branch(repo_path: str, branch: str) -> None:
    _run(repo_path, ["branch", "-M", branch])  # rename current branch, works before first commit too