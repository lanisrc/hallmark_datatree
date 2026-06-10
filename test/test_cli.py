# Copyright 2026 the Hallmark Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
from pathlib        import Path
from contextlib     import contextmanager
from click.testing  import CliRunner
from git import Repo as GitRepo

from hallmark import ParaFrame
from hallmark.cli import hallmark
from hallmark.downloader import DownloadError


@contextmanager
def chdir(path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


files = [f"a{a}_i{i}.h5"
         for a in [0, 0.75, 0.975]
         for i in [0, 30, 60, 90]]

def parse(result):
    output = result.output.split('\n')[1:-1]
    return len(output), [f.strip(' ') for f in output]

def test_cli():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(hallmark, ["init", "repo"])
        assert result.exit_code == 0

        with chdir("repo"):
            assert Path(".hm").is_dir()

            for file in files:
                Path(file).write_text("test\n", encoding="utf-8")

            result = runner.invoke(hallmark, ["add", "a{a}_i{i}.h5"])
            assert result.exit_code == 0

            c, ls = parse(result)
            assert c == 12
            assert sorted(ls) == sorted(files)

            result = runner.invoke(hallmark, ["commit", "-m", "Commit test"])
            assert result.exit_code == 0
            assert "Committed staged state changes." in result.output

            result = runner.invoke(hallmark, ["checkout", "experiment"])
            assert result.exit_code == 0
            assert 'Switched to branch "experiment".' in result.output

            Path("a0_i0.h5").unlink()
            Path("a0_i30.h5").unlink()
            Path("a0_i60.h5").unlink()
            Path("a0_i90.h5").unlink()
            Path("a0.75_i0.h5").unlink()
            Path("a0.75_i30.h5").unlink()
            Path("a0.75_i60.h5").unlink()
            Path("a0.75_i90.h5").unlink()
            Path("a0.975_i0.h5").unlink()
            Path("a0.975_i30.h5").unlink()
            Path("a0.975_i60.h5").unlink()
            Path("a0.975_i90.h5").unlink()
            Path("a1_i45.h5").write_text("a1_i45.h5\n", encoding="utf-8")
            result = runner.invoke(hallmark, ["add", "."])
            assert result.exit_code == 0
            result = runner.invoke(hallmark, ["commit", "-m", "Commit experiment"])
            assert result.exit_code == 0

            result = runner.invoke(hallmark, ["checkout", "main"])
            assert result.exit_code == 0
            assert not Path("a1_i45.h5").exists()

            Path("a0_i0.h5").write_text("dirty\n", encoding="utf-8")
            result = runner.invoke(hallmark, ["checkout", "experiment"])
            assert result.exit_code != 0
            assert "has uncommitted changes" in result.output


def test_cli_add_dot_and_explicit_paths():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(hallmark, ["init", "repo"])

        with chdir("repo"):
            Path("a0_i0.h5").write_text("a0_i0.h5\n", encoding="utf-8")
            Path("a0_i30.h5").write_text("a0_i30.h5\n", encoding="utf-8")

            result = runner.invoke(hallmark, ["add", "a{a}_i{i}.h5"])
            assert result.exit_code == 0

            Path("a0_i0.h5").unlink()
            Path("a1_i45.h5").write_text("a1_i45.h5\n", encoding="utf-8")
            result = runner.invoke(hallmark, ["add", "."])
            assert result.exit_code == 0
            manifest = Path(".hm/data.tsv").read_text(encoding="utf-8")
            assert "a0_i0.h5" not in manifest
            assert "\t1\t45" in manifest or ",1,45" not in manifest

            Path("top1.h5").write_text("top1.h5\n", encoding="utf-8")
            Path("top2.h5").write_text("top2.h5\n", encoding="utf-8")
            result = runner.invoke(hallmark, ["add", "top1.h5", "top2.h5"])
            assert result.exit_code != 0
            assert "explicit path add is not supported" in result.output


def test_cli_add_regex_flag(monkeypatch):
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(hallmark, ["init", "repo"])

        with chdir("repo"):
            called = {}

            def fake_add(self, fmt, encoding=False):
                called["fmt"] = fmt
                called["encoding"] = encoding
                return ParaFrame([{"path": "am0.5_i30.h5"}])

            monkeypatch.setattr("hallmark.cli.Repo.add", fake_add)
            result = runner.invoke(hallmark, ["add", "--regex", "."])

            assert result.exit_code == 0
            assert called == {"fmt": ".", "encoding": True}


def test_cli_status():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(hallmark, ["init", "repo"])

        with chdir("repo"):
            Path("a0_i0.h5").write_text("a0_i0.h5\n", encoding="utf-8")
            Path("a0_i30.h5").write_text("a0_i30.h5\n", encoding="utf-8")
            runner.invoke(hallmark, ["add", "a{a}_i{i}.h5"])
            runner.invoke(hallmark, ["commit", "-m", "Commit test"])

            Path("a0_i0.h5").write_text("changed\n", encoding="utf-8")
            Path("a0_i30.h5").unlink()
            Path("untracked.h5").write_text("untracked\n", encoding="utf-8")

            result = runner.invoke(hallmark, ["status"])
            assert result.exit_code == 0
            assert "On branch main" in result.output
            assert "Changes not staged for commit:" in result.output
            assert "modified:   a0_i0.h5" in result.output
            assert "deleted:   a0_i30.h5" in result.output
            assert "Untracked files:" in result.output
            assert "untracked.h5" in result.output


def test_cli_set_config_and_add_dot():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(hallmark, ["init", "repo"])

        with chdir("repo"):
            result = runner.invoke(
                hallmark,
                [
                    "set-config",
                    "--fmt", "b{a}_i{i}.h5",
                    "--remote-name", "origin",
                    "--remote-url", "https://example.com/path",
                    "--encoding", r"aspin=m([0-9]+(\.[0-9]+)?|\.[0-9]+)",
                ],
            )
            assert result.exit_code == 0
            assert "Updated hallmark config." in result.output

            Path("b0_i0.h5").write_text("b0_i0.h5\n", encoding="utf-8")
            Path("b0_i30.h5").write_text("b0_i30.h5\n", encoding="utf-8")

            result = runner.invoke(hallmark, ["add", "."])
            assert result.exit_code == 0

            manifest = Path(".hm/data.tsv").read_text(encoding="utf-8")
            assert "sha1\ta\ti" in manifest
            config = Path(".hm/config.yml").read_text(encoding="utf-8")
            assert "fmt: b{a}_i{i}.h5" in config
            assert "name: origin" in config
            assert "url: https://example.com/path" in config
            assert r"aspin: m([0-9]+(\.[0-9]+)?|\.[0-9]+)" in config


def test_cli_status_shows_staged_state_after_set_config():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(hallmark, ["init", "repo"])

        with chdir("repo"):
            result = runner.invoke(hallmark, ["set-config", "--fmt", "b{a}_i{i}.h5"])
            assert result.exit_code == 0

            result = runner.invoke(hallmark, ["status"])

            assert result.exit_code == 0
            assert "Changes to be committed:" in result.output
            assert "state:   config.yml" in result.output
            assert "nothing to commit, working tree clean" not in result.output

            result = runner.invoke(hallmark, ["commit", "-m", "config only"])
            assert result.exit_code == 0
            assert "Committed staged state changes." in result.output


def test_cli_set_config_rejects_malformed_encoding():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(hallmark, ["init", "repo"])

        with chdir("repo"):
            result = runner.invoke(hallmark, ["set-config", "--encoding", "aspin"])
            assert result.exit_code != 0
            assert "FIELD=REGEX" in result.output


def test_cli_log():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(hallmark, ["init", "repo"])

        with chdir("repo"):
            result = runner.invoke(hallmark, ["log"])
            assert result.exit_code == 0
            expected = GitRepo(".hm").git.log()
            assert result.output.strip() == expected.strip()

            Path("a0_i0.h5").write_text("a0_i0.h5\n", encoding="utf-8")
            runner.invoke(hallmark, ["add", "a{a}_i{i}.h5"])
            runner.invoke(hallmark, ["commit", "-m", "add first file"])

            Path("a0_i30.h5").write_text("a0_i30.h5\n", encoding="utf-8")
            runner.invoke(hallmark, ["add", "."])
            runner.invoke(hallmark, ["commit", "-m", "add second file"])

            result = runner.invoke(hallmark, ["log"])
            assert result.exit_code == 0
            expected = GitRepo(".hm").git.log()
            assert result.output.strip() == expected.strip()


def test_cli_branch_lists_local_branches_and_marks_current():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(hallmark, ["init", "repo"])

        with chdir("repo"):
            Path("a0_i0.h5").write_text("a0_i0.h5\n", encoding="utf-8")
            runner.invoke(hallmark, ["add", "a{a}_i{i}.h5"])
            runner.invoke(hallmark, ["commit", "-m", "add first file"])
            runner.invoke(hallmark, ["checkout", "experiment"])

            result = runner.invoke(hallmark, ["branch"])

            assert result.exit_code == 0
            assert "  main" in result.output
            assert "* experiment" in result.output


def test_clone_existing_destination_reports_plain_git_stderr():
    runner = CliRunner()
    with runner.isolated_filesystem():
        source = Path("source")
        result = runner.invoke(hallmark, ["init", str(source)])
        assert result.exit_code == 0

        target = Path("repo3")
        target.mkdir(parents=True)
        (target / "placeholder.txt").write_text("test\n", encoding="utf-8")

        result = runner.invoke(
            hallmark,
            ["clone", "--no-fetch-data", str(source / ".hm"), str(target)],
        )

        assert result.exit_code == 0
        assert not result.output.startswith("Error:")
        assert "stderr:" not in result.output
        assert "Clone failed:" not in result.output
        assert (
            result.output.strip()
            == "fatal: destination path 'repo3' already exists and "
            "is not an empty directory."
        )


def test_clone_copies_committed_hallmark_state():
    runner = CliRunner()
    with runner.isolated_filesystem():
        source = Path("source")
        result = runner.invoke(hallmark, ["init", str(source)])
        assert result.exit_code == 0

        GitRepo(str(source / ".hm")).index.commit("commit initial hallmark state")

        result = runner.invoke(
            hallmark,
            ["clone", "--no-fetch-data", str(source / ".hm"), "target"],
        )

        assert result.exit_code == 0
        assert 'Successfully cloned to "target"' in result.output
        assert Path("target/.hm").is_dir()
        assert Path("target/.hm/config.yml").exists()
        assert Path("target/.hm/meta.yml").exists()
        assert Path("target/.hm/data.tsv").exists()


def test_clone_reports_download_error_cleanly(monkeypatch):
    runner = CliRunner()
    with runner.isolated_filesystem():
        source = Path("source")
        result = runner.invoke(hallmark, ["init", str(source)])
        assert result.exit_code == 0

        GitRepo(str(source / ".hm")).index.commit("commit initial hallmark state")

        def boom(*args, **kwargs):
            raise DownloadError("Remote URL not configured in config.yml")

        monkeypatch.setattr("hallmark.cli.download_remote_data", boom)

        result = runner.invoke(
            hallmark,
            ["clone", str(source / ".hm"), "target"],
        )

        assert result.exit_code != 0
        assert "Remote URL not configured in config.yml" in result.output
