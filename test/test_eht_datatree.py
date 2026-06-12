from pathlib import Path
import pytest
from hallmark import ParaFrame
from hallmark.eht_datatree import read_inventory, validate, build_tree

INVENTORY_CONTENT = """\
README.md
INVENTORY.txt
LICENSE.txt
run.sh*
uvfits/
uvfits/convert_stokesI.py*
uvfits/SR1_M87_2017_095_hi_hops_netcal_StokesI.uvfits
uvfits/SR1_M87_2017_095_lo_hops_netcal_StokesI.uvfits
txt/
txt/dump_txt.py*
txt/SR1_M87_2017_095_hi_hops_netcal_StokesI.txt
txt/SR1_M87_2017_095_lo_hops_netcal_StokesI.txt
csv/
csv/dump_csv.py*
csv/SR1_M87_2017_095_hi_hops_netcal_StokesI.csv
csv/SR1_M87_2017_095_lo_hops_netcal_StokesI.csv
EHTC_FirstM87Results_Apr2019_uvfits.tgz
EHTC_FirstM87Results_Apr2019_txt.tgz
EHTC_FirstM87Results_Apr2019_csv.tgz
"""

# create test inventory file
def _write_inventory(root: Path, content: str) -> None:
    (root / "INVENTORY.txt").write_text(content, encoding="utf-8")

# write inventory file fixture into temporary directory
@pytest.fixture
def inventory_dir(tmp_path):
    _write_inventory(tmp_path, INVENTORY_CONTENT)
    return tmp_path

# create fixture for read_inventory result to use in multiple tests
@pytest.fixture
def inventory_result(inventory_dir):
    return read_inventory(inventory_dir)

# create test dataset fixture
@pytest.fixture
def eht_dataset(tmp_path):

    # create subdirectories
    (tmp_path / "csv").mkdir()
    (tmp_path / "txt").mkdir()
    (tmp_path / "uvfits").mkdir()

    # write meta files
    for file_name in ["README.md", "LICENSE.txt", "run.sh"]:
        (tmp_path / file_name).write_text(file_name, encoding="utf-8")

    # write INVENTORY.txt mirroring the real dataset structure
    _write_inventory(tmp_path, INVENTORY_CONTENT)

    # write script files
    for file_name in ["csv/dump_csv.py", 
                      "txt/dump_txt.py", 
                      "uvfits/convert_stokesI.py"]:
        (tmp_path / file_name).write_text(file_name, encoding="utf-8")

    # write drive files
    for file_name in [
        "EHTC_FirstM87Results_Apr2019_csv.tgz",
        "EHTC_FirstM87Results_Apr2019_txt.tgz",
        "EHTC_FirstM87Results_Apr2019_uvfits.tgz",
    ]:
        (tmp_path / file_name).write_text(file_name, encoding="utf-8")

    # write data files — 2 stems, 3 formats each
    for stem in [
        "SR1_M87_2017_095_hi_hops_netcal_StokesI",
        "SR1_M87_2017_095_lo_hops_netcal_StokesI",
    ]:
        for ext in ["csv", "txt", "uvfits"]:
            (tmp_path / ext / f"{stem}.{ext}").write_text(stem, encoding="utf-8")

    return tmp_path

# create fixture for build_tree result to use in multiple tests
@pytest.fixture
def sample_tree(eht_dataset):
    return build_tree(eht_dataset)

### read_inventory tests ###

def test_read_inventory_returns_list(inventory_result):
    assert isinstance(inventory_result, list)


def test_read_inventory_skips_directory_lines(inventory_result):
    assert not any(entry.endswith("/") for entry in inventory_result)


def test_read_inventory_strips_executable_marker(inventory_result):
    assert not any(entry.endswith("*") for entry in inventory_result)


def test_read_inventory_includes_top_level_files(inventory_result):
    assert "README.md" in inventory_result
    assert "LICENSE.txt" in inventory_result
    assert "INVENTORY.txt" in inventory_result
    assert "run.sh" in inventory_result


def test_read_inventory_includes_scripts(inventory_result):
    assert "uvfits/convert_stokesI.py" in inventory_result
    assert "txt/dump_txt.py" in inventory_result
    assert "csv/dump_csv.py" in inventory_result


def test_read_inventory_includes_data_files(inventory_result):
    assert "uvfits/SR1_M87_2017_095_hi_hops_netcal_StokesI.uvfits" in inventory_result
    assert "txt/SR1_M87_2017_095_hi_hops_netcal_StokesI.txt" in inventory_result
    assert "csv/SR1_M87_2017_095_hi_hops_netcal_StokesI.csv" in inventory_result


def test_read_inventory_includes_drives(inventory_result):
    assert "EHTC_FirstM87Results_Apr2019_uvfits.tgz" in inventory_result

# needs its own fixture to test blank lines handling
def test_read_inventory_skips_blank_lines(tmp_path):
    _write_inventory(tmp_path, "\nREADME.md\n\nLICENSE.txt\n")
    result = read_inventory(tmp_path)
    assert result == ["README.md", "LICENSE.txt"]

# needs its own fixture to test for missing inventory file
def test_read_inventory_raises_if_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_inventory(tmp_path)


#### validate tests ####

def test_validate_returns_true_when_all_present(inventory_dir, inventory_result):
    # convert inventory_result to a set to work with validate's expected input
    tracked = set(inventory_result)
    assert validate(inventory_dir, tracked) is True


def test_validate_returns_false_when_files_missing(inventory_dir):
    assert validate(inventory_dir, set()) is False


def test_validate_reports_only_missing_files(inventory_dir, capsys):
    tracked = {"README.md", "INVENTORY.txt", "LICENSE.txt"}
    validate(inventory_dir, tracked)
    # capture printed output of missing files
    output = capsys.readouterr().out
    assert "run.sh" in output
    assert "README.md" not in output

# needs its own fixture to test for missing inventory file
def test_validate_raises_if_no_inventory(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate(tmp_path, set())


### build_tree tests ###

def test_build_tree_returns_dict(sample_tree):
    assert isinstance(sample_tree, dict)


def test_build_tree_has_correct_keys(sample_tree):
    assert set(sample_tree.keys()) == {"meta", "drives", "data"}


def test_build_tree_meta_is_paraframe(sample_tree):
    assert isinstance(sample_tree["meta"], ParaFrame)


def test_build_tree_drives_is_paraframe(sample_tree):
    assert isinstance(sample_tree["drives"], ParaFrame)


def test_build_tree_data_is_dict(sample_tree):
    assert isinstance(sample_tree["data"], dict)


def test_build_tree_meta_has_correct_files(sample_tree):
    meta_path = set(sample_tree["meta"]["path"])
    assert "README.md" in meta_path
    assert "LICENSE.txt" in meta_path
    assert "INVENTORY.txt" in meta_path
    assert "run.sh" in meta_path
    assert "uvfits/convert_stokesI.py" in meta_path
    assert "txt/dump_txt.py" in meta_path
    assert "csv/dump_csv.py" in meta_path


def test_build_tree_meta_has_only_meta_files(sample_tree):
    meta_path = set(sample_tree["meta"]["path"])
    assert not any(".uvfits" in path for path in meta_path)
    assert not any(".tgz" in path for path in meta_path)


def test_build_tree_drives_has_three_files(sample_tree):
    assert len(sample_tree["drives"]) == 3

def test_build_tree_drives_all_tgz(sample_tree):
    assert all(path.endswith(".tgz") for path in sample_tree["drives"]["path"])


def test_build_tree_data_has_two_stems(sample_tree):
    assert len(sample_tree["data"]) == 2


def test_build_tree_data_stems_are_paraframes(sample_tree):
    for stem, pf in sample_tree["data"].items():
        assert isinstance(pf, ParaFrame), f"{stem} is not a ParaFrame"


def test_build_tree_each_stem_has_three_files(sample_tree):
    for stem, pf in sample_tree["data"].items():
        assert len(pf) == 3, f"{stem} has {len(pf)} files, expected 3"


def test_build_tree_each_stem_has_correct_columns(sample_tree):
    for stem, pf in sample_tree["data"].items():
        assert set(pf.columns) == {"path", "ext", "year", "day", "band"}, \
                                  f"{stem} has incorrect columns: {pf.columns}"

def test_build_tree_each_stem_has_all_three_formats(sample_tree):
    for stem, pf in sample_tree["data"].items():
        assert set(pf["ext"].unique()) == {"csv", "txt", "uvfits"}, (
            f"{stem} has wrong formats: {set(pf['ext'].unique())}"
            )


def test_build_tree_no_file_in_multiple_branches(sample_tree):
    meta_paths  = set(sample_tree["meta"]["path"])
    drive_paths = set(sample_tree["drives"]["path"])
    data_paths  = {
        path
        for pf in sample_tree["data"].values()
        for path in pf["path"]
    }
    # checks that the three branches have no common files
    assert meta_paths.isdisjoint(drive_paths)
    assert meta_paths.isdisjoint(data_paths)
    assert drive_paths.isdisjoint(data_paths)


def test_build_tree_validate_passes(sample_tree, eht_dataset):
    tracked = set()
    for _, row in sample_tree["meta"].iterrows():
        tracked.add(row["path"])
    for _, row in sample_tree["drives"].iterrows():
        tracked.add(row["path"])
    for pf in sample_tree["data"].values():
        for _, row in pf.iterrows():
            tracked.add(row["path"])
    assert validate(eht_dataset, tracked) is True