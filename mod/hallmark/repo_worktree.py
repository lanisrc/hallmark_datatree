from __future__ import annotations

import os
from pathlib import Path

from .repo_config import branch_fmt, path_from_row
from .error import CheckoutError


def effective_cwd(repo) -> Path:
    if repo.worktree is None:
        raise RuntimeError("cannot inspect files in a bare repository " \
        "without a worktree")

    cwd = Path.cwd().resolve()
    worktree = Path(repo.worktree).resolve()
    try:
        cwd.relative_to(worktree)
    except ValueError:
        return worktree
    return cwd


def filtered_paraframe(repo, pf):
    root = effective_cwd(repo)
    worktree = Path(repo.worktree)
    if root == worktree:
        return pf

    prefix = str(root.relative_to(worktree))
    mask = pf["path"].astype(str).str.startswith(prefix + os.sep)
    return pf[mask]


def tracked_paths(repo) -> set[Path]:
    fmt = branch_fmt(repo)
    return {path_from_row(repo, row, fmt) for _, row in repo.state.data.iterrows()}


def ensure_clean_tracked_files(repo) -> None:
    if repo.worktree is None:
        raise CheckoutError("cannot checkout without a worktree")

    for _, row in repo.state.data.iterrows():
        rel_path = path_from_row(repo, row)
        path = repo.worktree / rel_path
        if not path.exists():
            raise CheckoutError(
                f'tracked file "{rel_path}" is missing; commit or \
                restore it before checkout')
        if repo.checksum(path) != row["sha1"]:
            raise CheckoutError(
                f'tracked file "{rel_path}" has uncommitted changes; \
                commit them before checkout')

    if repo.dothm.index.diff("HEAD"):
        raise CheckoutError(
            "you have uncommitted hallmark state changes — " \
            "commit them before checkout")
