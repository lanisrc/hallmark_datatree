from __future__ import annotations

from string import Formatter
from pathlib import Path
from typing import Dict, Optional


def ensure_branch_data_spec(config: dict) -> dict:
    data = config.get("data")
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        config["data"] = [{}]
    return config["data"][0]


def branch_data_spec(repo) -> dict:
    data = repo.state.config.get("data")
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise RuntimeError('branch config must define exactly ' \
        'one entry under "data" in config.yml')
    return data[0]


def branch_fmt(repo) -> str:
    fmt = branch_data_spec(repo).get("fmt")
    if not isinstance(fmt, str) or not fmt.strip():
        raise RuntimeError('branch config must define one ' \
        'non-empty data[0].fmt in config.yml')
    return fmt


def set_branch_fmt(repo, fmt: str) -> None:
    set_config(repo, fmt=fmt)


def set_config(
    repo,
    *,
    fmt: Optional[str] = None,
    remote_name: Optional[str] = None,
    remote_url: Optional[str] = None,
    encoding_updates: Optional[Dict[str, str]] = None,
) -> dict:
    config = repo.state.config

    spec = ensure_branch_data_spec(config)
    updated_spec = {}

    if fmt is not None:
        updated_spec["fmt"] = fmt
    elif "fmt" in spec:
        updated_spec["fmt"] = spec["fmt"]

    encoding_value = spec.get("encoding")
    if encoding_updates:
        if not isinstance(encoding_value, dict):
            encoding_value = {}
        encoding_value = {**encoding_value, **encoding_updates}
    if "encoding" in spec or encoding_updates is not None:
        updated_spec["encoding"] = encoding_value

    for key, value in spec.items():
        if key not in {"fmt", "encoding"}:
            updated_spec[key] = value
    config["data"][0] = updated_spec

    if remote_name is not None or remote_url is not None:
        remote = config.get("remote")
        if not isinstance(remote, dict):
            remote = {}

        updated_remote = {}
        if remote_name is not None:
            updated_remote["name"] = remote_name
        elif "name" in remote:
            updated_remote["name"] = remote["name"]

        if remote_url is not None:
            updated_remote["url"] = remote_url
        elif "url" in remote:
            updated_remote["url"] = remote["url"]

        for key, value in remote.items():
            if key not in {"name", "url"}:
                updated_remote[key] = value
        config["remote"] = updated_remote

    return config


def branch_encodings(repo) -> list[dict]:
    spec = branch_data_spec(repo)
    return [spec] if isinstance(spec.get("encoding"), dict) else []


def fmt_fields(fmt: str) -> list[str]:
    fields: list[str] = []
    for _, field_name, _, _ in Formatter().parse(fmt):
        if field_name and field_name not in fields:
            fields.append(field_name)
    return fields


def coerce_fmt_value(value: str, spec: str):
    if not spec:
        return value
    if spec.endswith("d"):
        return int(float(value))
    if spec[-1] in {"f", "F", "g", "G", "e", "E"}:
        return float(value)
    return value


def row_to_path(row, fmt: str) -> Path:
    values = {}
    for _, field_name, format_spec, _ in Formatter().parse(fmt):
        if field_name:
            values[field_name] = coerce_fmt_value(str(row[field_name]), format_spec)
    return Path(fmt.format(**values))


def path_from_row(repo, row, fmt: Optional[str] = None) -> Path:
    return row_to_path(row, fmt or branch_fmt(repo))
