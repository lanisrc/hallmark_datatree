from __future__ import annotations

from io import StringIO

import pandas as pd
import yaml
from git.exc import GitCommandError

from .state import State


def load_branch_config(repo, branch: str) -> dict:
    try:
        return yaml.safe_load(repo.dothm.git.show(f"{branch}:config.yml")) or {}
    except GitCommandError:
        return dict(repo.state.config)


def load_branch_meta(repo, branch: str) -> dict:
    try:
        return yaml.safe_load(repo.dothm.git.show(f"{branch}:meta.yml")) or {}
    except GitCommandError:
        return dict(repo.state.meta)


def load_branch_data(repo, branch: str) -> State:
    if branch in {head.name for head in repo.dothm.heads}:
        data = repo.dothm.git.show(f"{branch}:data.tsv")
        frame = State().data if not data.strip() else None
        if frame is None:
            parsed = pd.read_csv(StringIO(data), sep="\t", dtype=str)
        else:
            parsed = frame
        return State(
            load_branch_config(repo, branch),
            load_branch_meta(repo, branch),
            parsed,
        )

    return State(
        dict(repo.state.config),
        dict(repo.state.meta),
        repo.state.data.copy(),
    )


def load_head_state(repo) -> State:
    try:
        data = repo.dothm.git.show("HEAD:data.tsv")
    except GitCommandError:
        return State(
            dict(repo.state.config),
            dict(repo.state.meta),
            State().data.copy(),
        )

    if data.strip():
        parsed = pd.read_csv(StringIO(data), sep="\t", dtype=str)
    else:
        parsed = State().data.copy()

    return State(
        load_branch_config(repo, "HEAD"),
        load_branch_meta(repo, "HEAD"),
        parsed,
    )
