from pathlib import Path
import pytest
from hallmark.eht_datatree import read_inventory, validate, build_tree, ParaFrame

INVENTORY_CONTENT = """\
README.md
INVENTORY.txt
LICENSE.txt
run.sh*
uvfits/
uvfits/convert_stokesI.py*
uvfits/SR1_M87_2017_095_hi_hops_netcal_StokesI.uvfits
txt/
txt/dump_txt.py*
txt/SR1_M87_2017_095_hi_hops_netcal_StokesI.txt
csv/
csv/dump_csv.py*
csv/SR1_M87_2017_095_hi_hops_netcal_StokesI.csv
EHTC_FirstM87Results_Apr2019_uvfits.tgz
"""

# create test inventory file
def _write_inventory(root: Path, content: str) -> None:
    (root / "INVENTORY.txt").write_text(content, encoding="utf-8")

# test fixture to provide path to EHT dataset, skipping tests if not found
@pytest.fixture
def eht_dataset():
    root = Path("~/eht_m87_2019/EHTC_FirstM87Results_Apr2019").expanduser()
    if not root.exists():
        pytest.skip("EHT dataset not found — skipping")
    return root

#read_inventory tests
def test_read_inventory_returns_list(tmp_path):
    _write_inventory(tmp_path, INVENTORY_CONTENT)
    result = read_inventory(tmp_path)
    assert isinstance(result, list)


def test_read_inventory_skips_directory_lines(tmp_path):
    _write_inventory(tmp_path, INVENTORY_CONTENT)
    result = read_inventory(tmp_path)
    assert not any(entry.endswith("/") for entry in result)


def test_read_inventory_strips_executable_marker(tmp_path):
    _write_inventory(tmp_path, INVENTORY_CONTENT)
    result = read_inventory(tmp_path)
    assert not any(entry.endswith("*") for entry in result)


def test_read_inventory_includes_top_level_files(tmp_path):
    _write_inventory(tmp_path, INVENTORY_CONTENT)
    result = read_inventory(tmp_path)
    assert "README.md" in result
    assert "LICENSE.txt" in result
    assert "INVENTORY.txt" in result
    assert "run.sh" in result


def test_read_inventory_includes_scripts(tmp_path):
    _write_inventory(tmp_path, INVENTORY_CONTENT)
    result = read_inventory(tmp_path)
    assert "uvfits/convert_stokesI.py" in result
    assert "txt/dump_txt.py" in result
    assert "csv/dump_csv.py" in result


def test_read_inventory_includes_data_files(tmp_path):
    _write_inventory(tmp_path, INVENTORY_CONTENT)
    result = read_inventory(tmp_path)
    assert "uvfits/SR1_M87_2017_095_hi_hops_netcal_StokesI.uvfits" in result
    assert "txt/SR1_M87_2017_095_hi_hops_netcal_StokesI.txt" in result
    assert "csv/SR1_M87_2017_095_hi_hops_netcal_StokesI.csv" in result


def test_read_inventory_includes_drives(tmp_path):
    _write_inventory(tmp_path, INVENTORY_CONTENT)
    result = read_inventory(tmp_path)
    assert "EHTC_FirstM87Results_Apr2019_uvfits.tgz" in result


def test_read_inventory_skips_blank_lines(tmp_path):
    content = "\nREADME.md\n\nLICENSE.txt\n"
    _write_inventory(tmp_path, content)
    result = read_inventory(tmp_path)
    assert result == ["README.md", "LICENSE.txt"]


def test_read_inventory_raises_if_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_inventory(tmp_path)


# validate tests
def test_validate_returns_true_when_all_present(tmp_path):
    _write_inventory(tmp_path, INVENTORY_CONTENT)
    tracked = {
        "README.md",
        "INVENTORY.txt",
        "LICENSE.txt",
        "run.sh",
        "uvfits/convert_stokesI.py",
        "uvfits/SR1_M87_2017_095_hi_hops_netcal_StokesI.uvfits",
        "txt/dump_txt.py",
        "txt/SR1_M87_2017_095_hi_hops_netcal_StokesI.txt",
        "csv/dump_csv.py",
        "csv/SR1_M87_2017_095_hi_hops_netcal_StokesI.csv",
        "EHTC_FirstM87Results_Apr2019_uvfits.tgz",
    }
    assert validate(tmp_path, tracked) is True


def test_validate_returns_false_when_files_missing(tmp_path):
    _write_inventory(tmp_path, INVENTORY_CONTENT)
    assert validate(tmp_path, set()) is False


def test_validate_reports_only_missing_files(tmp_path, capsys):
    _write_inventory(tmp_path, INVENTORY_CONTENT)
    tracked = {"README.md", "INVENTORY.txt", "LICENSE.txt"}
    validate(tmp_path, tracked)
    output = capsys.readouterr().out
    assert "run.sh" in output
    assert "README.md" not in output


def test_validate_raises_if_no_inventory(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate(tmp_path, set())

# build_tree tests
def test_build_tree_returns_dict(eht_dataset):
    tree = build_tree(eht_dataset)
    assert isinstance(tree, dict)


def test_build_tree_has_correct_keys(eht_dataset):
    tree = build_tree(eht_dataset)
    assert set(tree.keys()) == {"meta", "drives", "data"}


def test_build_tree_meta_is_paraframe(eht_dataset):
    tree = build_tree(eht_dataset)
    assert isinstance(tree["meta"], ParaFrame)


def test_build_tree_drives_is_paraframe(eht_dataset):
    tree = build_tree(eht_dataset)
    assert isinstance(tree["drives"], ParaFrame)


def test_build_tree_data_is_dict(eht_dataset):
    tree = build_tree(eht_dataset)
    assert isinstance(tree["data"], dict)


def test_build_tree_meta_has_correct_files(eht_dataset):
    tree = build_tree(eht_dataset)
    paths = set(tree["meta"]["path"])
    assert "README.md" in paths
    assert "LICENSE.txt" in paths
    assert "INVENTORY.txt" in paths
    assert "run.sh" in paths
    assert "uvfits/convert_stokesI.py" in paths
    assert "txt/dump_txt.py" in paths
    assert "csv/dump_csv.py" in paths


def test_build_tree_meta_has_no_data_files(eht_dataset):
    tree = build_tree(eht_dataset)
    paths = set(tree["meta"]["path"])
    assert not any(".uvfits" in p for p in paths)
    assert not any(".tgz" in p for p in paths)


def test_build_tree_drives_has_three_files(eht_dataset):
    tree = build_tree(eht_dataset)
    assert len(tree["drives"]) == 3

def test_build_tree_drives_all_tgz(eht_dataset):
    tree = build_tree(eht_dataset)
    assert all(p.endswith(".tgz") for p in tree["drives"]["path"])


def test_build_tree_data_has_eight_stems(eht_dataset):
    tree = build_tree(eht_dataset)
    assert len(tree["data"]) == 8


def test_build_tree_data_stems_are_paraframes(eht_dataset):
    tree = build_tree(eht_dataset)
    for stem, pf in tree["data"].items():
        assert isinstance(pf, ParaFrame), f"{stem} is not a ParaFrame"


def test_build_tree_each_stem_has_three_files(eht_dataset):
    tree = build_tree(eht_dataset)
    for stem, pf in tree["data"].items():
        assert len(pf) == 3, f"{stem} has {len(pf)} files, expected 3"


def test_build_tree_each_stem_has_correct_columns(eht_dataset):
    tree = build_tree(eht_dataset)
    for stem, pf in tree["data"].items():
        assert set(pf.columns) == {"path", "ext", "year", "day", "band"}

def test_build_tree_each_stem_has_all_three_formats(eht_dataset):
    tree = build_tree(eht_dataset)
    for stem, pf in tree["data"].items():
        assert set(pf["ext"].unique()) == {"csv", "txt", "uvfits"}


def test_build_tree_no_file_in_multiple_branches(eht_dataset):
    tree = build_tree(eht_dataset)
    meta_paths  = set(tree["meta"]["path"])
    drive_paths = set(tree["drives"]["path"])
    data_paths  = {
        path
        for pf in tree["data"].values()
        for path in pf["path"]
    }
    assert meta_paths.isdisjoint(drive_paths)
    assert meta_paths.isdisjoint(data_paths)
    assert drive_paths.isdisjoint(data_paths)


def test_build_tree_validate_passes(eht_dataset):
    tree = build_tree(eht_dataset)
    tracked = set()
    for _, row in tree["meta"].iterrows():
        tracked.add(row["path"])
    for _, row in tree["drives"].iterrows():
        tracked.add(row["path"])
    for pf in tree["data"].values():
        for _, row in pf.iterrows():
            tracked.add(row["path"])
    assert validate(eht_dataset, tracked) is True