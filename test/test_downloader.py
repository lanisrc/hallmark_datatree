from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from hallmark.downloader import DownloadError, _resolve_remote_path, \
download_remote_data


def test_resolve_remote_path_uses_explicit_path():
    row = pd.Series({"path": "nested/file.txt", "sha1": "abc"})

    assert _resolve_remote_path(row, []) == Path("nested/file.txt")


def test_resolve_remote_path_builds_path_from_data_format():
    row = pd.Series(
        {
            "sha1": "abc",
            "release": "SR1",
            "source": "M87",
            "year": 2017,
            "doy": 95,
            "band": "hi",
            "pipeline": "hops",
            "step": "netcal",
            "type": "StokesI",
        }
    )
    data_config = [
        {
            "fmt": (
                "{release}_{source}_{year}_{doy:03d}_{band}_"
                "{pipeline}_{step}_{type}.uvfits"
            )
        }
    ]

    assert _resolve_remote_path(row, data_config) == Path(
        "SR1_M87_2017_095_hi_hops_netcal_StokesI.uvfits"
    )


def test_resolve_remote_path_builds_typed_path_from_string_values():
    row = pd.Series(
        {
            "sha1": "abc",
            "release": "SR1",
            "source": "M87",
            "year": "2017",
            "doy": "95",
            "band": "hi",
            "pipeline": "hops",
            "step": "netcal",
            "type": "StokesI",
        }
    )
    data_config = [
        {
            "fmt": (
                "{release}_{source}_{year}_{doy:03d}_{band}_"
                "{pipeline}_{step}_{type}.uvfits"
            )
        }
    ]

    assert _resolve_remote_path(row, data_config) == Path(
        "SR1_M87_2017_095_hi_hops_netcal_StokesI.uvfits"
    )


def test_resolve_remote_path_raises_when_no_path_can_be_built():
    row = pd.Series({"sha1": "abc", "release": "SR1"})

    with pytest.raises(DownloadError, match="Unable to resolve download path"):
        _resolve_remote_path(row, [{"fmt": "{missing}.uvfits"}])


def test_download_remote_data_builds_urls_and_destinations_from_fmt(
        monkeypatch, tmp_path):
    captured = {}

    def fake_download_file(url, destination, sha1, chunk_size=8192):
        captured.setdefault("files", []).append((url, destination, sha1))
        return 123

    monkeypatch.setattr("hallmark.downloader._download_file", fake_download_file)

    repo = SimpleNamespace(
        state=SimpleNamespace(
            config={
                "data": [
                    {
                        "fmt": (
                            "{release}_{source}_{year}_{doy:03d}_{band}_"
                            "{pipeline}_{step}_{type}.uvfits"
                        )
                    }
                ],
                "remote": {"url": "https://example.com/data"},
            },
            data=pd.DataFrame(
                [
                    {
                        "sha1": "deadbeef",
                        "release": "SR1",
                        "source": "M87",
                        "year": "2017",
                        "doy": "95",
                        "band": "hi",
                        "pipeline": "hops",
                        "step": "netcal",
                        "type": "StokesI",
                    }
                ]
            ),
        )
    )

    result = download_remote_data(repo, tmp_path)

    assert result == {"succeeded": 1, "failed": 0, "total_bytes": 123, "errors": []}
    assert captured["files"] == [
        (
            "https://example.com/data/SR1_M87_2017_095_hi_hops_netcal_StokesI.uvfits",
            tmp_path / "SR1_M87_2017_095_hi_hops_netcal_StokesI.uvfits",
            "deadbeef",
        )
    ]
