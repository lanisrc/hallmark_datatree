from __future__ import annotations

from pathlib import Path

import parse
import pandas as pd

from .repo_config import fmt_fields, row_to_path


def manifest_frame_from_pf(pf, fmt: str) -> pd.DataFrame:
    if pf.empty:
        return pd.DataFrame(columns=["sha1", *fmt_fields(fmt)])

    parser = parse.compile(fmt)
    rows = []
    for _, row in pf.iterrows():
        parsed = parser.parse(str(row["path"]))
        if parsed is None:
            raise RuntimeError(f'failed to parse "{row["path"]}" \
                               using branch fmt "{fmt}"')
        rows.append({"sha1": row["sha1"], **{k: str(v) 
                                for k, v in parsed.named.items()}})
    return pd.DataFrame(rows, columns=["sha1", *fmt_fields(fmt)])


def manifest_map(state) -> dict[str, str]:
    if state.data.empty:
        return {}
    data = state.config.get("data")
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        return {}
    fmt = data[0].get("fmt")
    if not isinstance(fmt, str) or not fmt.strip():
        return {}
    return {
        str(row_to_path(row, fmt)): str(row["sha1"])
        for _, row in state.data.iterrows()
    }


def frame_from_paths(repo, rel_paths: list[Path]):
    records = [{"path": str(path)} for path in rel_paths]
    pf = repo.paraframe_cls(records, base_path=repo.worktree)
    if not pf.empty:
        pf["sha1"] = [repo.checksum(repo.worktree / path) for path in rel_paths]
    return pf
