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

# sample format string based on a real EHT dataset
sample_fmt = "{ext}/SR1_M87_{year}_{day}_{band}_hops_netcal_StokesI.{ext}"

# helper function to create test inventory file
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
    return build_tree(eht_dataset, sample_fmt)

### read_inventory tests ###

def test_read_inventory_returns_list(inventory_result):
    assert isinstance(inventory_result, list), \
    f"Expected list, got {type(inventory_result)}"


def test_read_inventory_skips_directory_lines(inventory_result):
    assert not any(entry.endswith("/") for entry in inventory_result), \
    "Expected no directory entries, but found some ending with '/'"


def test_read_inventory_strips_executable_marker(inventory_result):
    assert not any(entry.endswith("*") for entry in inventory_result), \
    "Expected no executable markers, but found some ending with '*'"

def test_read_inventory_includes_top_level_files(inventory_result):
    assert "README.md" in inventory_result, "No README.md found in inventory result"
    assert "LICENSE.txt" in inventory_result, "No LICENSE.txt found in inventory result"
    assert "INVENTORY.txt" in inventory_result, \
           "No INVENTORY.txt found in inventory result"
    assert "run.sh" in inventory_result, "No run.sh found in inventory result"


def test_read_inventory_includes_scripts(inventory_result):
    assert "uvfits/convert_stokesI.py" in inventory_result, \
           "uvfits/convert_stokesI.py not found in inventory result"
    assert "txt/dump_txt.py" in inventory_result, \
           "txt/dump_txt.py not found in inventory result"
    assert "csv/dump_csv.py" in inventory_result, \
           "csv/dump_csv.py not found in inventory result"


def test_read_inventory_includes_data_files(inventory_result):
    assert "uvfits/SR1_M87_2017_095_hi_hops_netcal_StokesI.uvfits" in inventory_result,\
"uvfits/SR1_M87_2017_095_hi_hops_netcal_StokesI.uvfits not found in inventory result"
    assert "txt/SR1_M87_2017_095_hi_hops_netcal_StokesI.txt" in inventory_result, \
        "txt/SR1_M87_2017_095_hi_hops_netcal_StokesI.txt not found in inventory result"
    assert "csv/SR1_M87_2017_095_hi_hops_netcal_StokesI.csv" in inventory_result, \
        "csv/SR1_M87_2017_095_hi_hops_netcal_StokesI.csv not found in inventory result"


def test_read_inventory_includes_drives(inventory_result):
    assert "EHTC_FirstM87Results_Apr2019_uvfits.tgz" in inventory_result, \
           "EHTC_FirstM87Results_Apr2019_uvfits.tgz not found in inventory result"

# needs its own fixture to test blank lines handling
def test_read_inventory_skips_blank_lines(tmp_path):
    _write_inventory(tmp_path, "\nREADME.md\n\nLICENSE.txt\n")
    result = read_inventory(tmp_path)
    assert result == ["README.md", "LICENSE.txt"], \
        f"Expected only README.md and LICENSE.txt, got {result}"

# needs its own fixture to test for missing inventory file
def test_read_inventory_raises_if_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_inventory(tmp_path)


#### validate tests ####

def test_validate_returns_true_when_all_present(inventory_dir, inventory_result):
    # convert inventory_result to a set to work with validate's expected input
    tracked = set(inventory_result)
    assert validate(inventory_dir, tracked) is True,\
          "validate did not return True when all inventory files were tracked"


def test_validate_returns_false_when_files_missing(inventory_dir):
    assert validate(inventory_dir, set()) is False, \
        "validate did not return False when files were missing"


def test_validate_reports_only_missing_files(inventory_dir, capsys):
    tracked = {"README.md", "INVENTORY.txt", "LICENSE.txt"}
    validate(inventory_dir, tracked)
    # capture printed output of missing files
    output = capsys.readouterr().out
    assert "run.sh" in output, "run.sh not in missing files"
    assert "README.md" not in output, "unexpected README.md file in missing files"

# needs its own fixture to test for missing inventory file
def test_validate_raises_if_no_inventory(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate(tmp_path, set())


### build_tree structure tests ###

def test_build_tree_raises_if_root_not_found(tmp_path):
    with pytest.raises(Exception): 
        build_tree(tmp_path / "nonexistent", sample_fmt)

def test_build_tree_returns_dict(sample_tree):
    assert isinstance(sample_tree, dict), f"expected dict, got {type(inventory_result)}"


def test_build_tree_has_correct_keys(sample_tree):
    assert set(sample_tree.keys()) == {"meta", "drives", "data"}, \
        f"unepected keys: {sample_tree.keys()}"


def test_build_tree_meta_is_paraframe(sample_tree):
    assert isinstance(sample_tree["meta"], ParaFrame), \
    f"meta is {type(sample_tree['meta'])} instead of ParaFrame"


def test_build_tree_drives_is_paraframe(sample_tree):
    assert isinstance(sample_tree["drives"], ParaFrame), \
    f"drives is {type(sample_tree['drives'])} instead of ParaFrame"


def test_build_tree_data_is_dict(sample_tree):
    assert isinstance(sample_tree["data"], dict), \
    f"data is {type(sample_tree['data'])} instead of dict"

def test_build_tree_path_column_always_present(sample_tree):
    assert "path" in sample_tree["meta"].columns, \
    "path column not present in meta branch"
    assert "path" in sample_tree["drives"].columns, \
    "path column not present in drives branch"
    for stem, pf in sample_tree["data"].values(): 
        assert "path" in pf.columns, \
    f"path column not present in {stem} data branch"

# needs unique dataset to test for ext column presence when not in fmt string
def test_build_tree_ext_column_always_present(tmp_path):
    (tmp_path / "csv").mkdir()
    (tmp_path / "csv" / "SR1_M87_2017_095_hi.csv").write_text(
        "data", encoding="utf-8")
    _write_inventory(tmp_path, "csv/SR1_M87_2017_095_hi.csv\n")
    fmt = "csv/SR1_M87_{year}_{day}_{band}.csv"
    tree = build_tree(tmp_path, fmt)
    for stem, pf in tree["data"].values(): 
        assert "ext" in pf.columns, f"ext column not present in {stem}"

### build_tree meta branch tests ###

def test_build_tree_meta_has_only_meta_files(sample_tree):
    meta_path = set(sample_tree["meta"]["path"])
    assert not any(".uvfits" in path for path in meta_path), \
        "meta branch contains data files"
    assert not any(".tgz" in path for path in meta_path), \
        "meta branch contains drive files"

def test_build_tree_meta_has_only_path_column(sample_tree):
    assert list(sample_tree["meta"].columns) == ["path"], \
        f"meta has unexpected columns: {list(sample_tree['meta'].columns)}"

### build_tree drive branch tests ###
def test_build_tree_drives_only_contains_archive_files(sample_tree):
    # verify every file in drives has a recognized archive extension
    archive_extensions = {".tgz", ".tar", ".gz", ".zip", ".bz2", ".xz", ".zst", ".7z", 
                          ".rar"}
    for path in sample_tree["drives"]["path"]:
        ext = Path(path).suffix
        assert ext in archive_extensions, f"{path} is not an archive file"


def test_build_tree_drives_has_only_path_column(sample_tree):
    assert list(sample_tree["drives"].columns) == ["path"]


# needs its own dataset to test for multiple drive extensions handling
def test_build_tree_drives_finds_multiple_extensions(tmp_path):
    # verify drives branch finds files with different archive extensions
    (tmp_path / "data.tgz").write_text("tgz", encoding="utf-8")
    (tmp_path / "data.zip").write_text("zip", encoding="utf-8")
    _write_inventory(tmp_path, "data.tgz\ndata.zip\n")
    tree = build_tree(tmp_path, "{name}")
    assert len(tree["drives"]) == 2
    # create list of all unique extensions in drives branch
    extensions = {Path(path).suffix for path in tree["drives"]["path"]}
    assert extensions == {".tgz", ".zip"}


def test_build_tree_drives_empty_when_no_archives(tmp_path):
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    _write_inventory(tmp_path, "README.md\n")
    tree = build_tree(tmp_path, "{name}")
    assert len(tree["drives"]) == 0, \
        f"length should be zero but len={len(tree['drives'])}"


def test_build_tree_drives_found_in_subdirectories(tmp_path):
    subdir = tmp_path / "archives"
    subdir.mkdir()
    (subdir / "data.tgz").write_text("tgz", encoding="utf-8")
    _write_inventory(tmp_path, "archives/data.tgz\n")
    tree = build_tree(tmp_path, "{name}")
    assert any("data.tgz" in path for path in tree["drives"]["path"])

#### build_tree data branch tests ###

def test_build_tree_data_has_two_stems(sample_tree):
    assert len(sample_tree["data"]) == 2


def test_build_tree_data_stems_are_paraframes(sample_tree):
    for stem, pf in sample_tree["data"].items():
        assert isinstance(pf, ParaFrame), f"{stem} is not a ParaFrame"


def test_build_tree_each_stem_has_three_files(sample_tree):
    for stem, pf in sample_tree["data"].items():
        assert len(pf) == 3, f"{stem} has {len(pf)} files, expected 3"


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


def test_build_tree_data_empty_when_no_fmt_matches(eht_dataset):
    # use a format that doesn't match any files to verify data branch is empty
    tree = build_tree(eht_dataset, "{ext}/NONEXISTENT_{year}_{day}.{ext}")
    assert len(tree["data"]) == 0

# needs unique dataset to test for single stem handling
def test_build_tree_single_stem(tmp_path):
    (tmp_path / "csv").mkdir()
    (tmp_path / "csv" / "SR1_M87_2017_095_hi_hops_netcal_StokesI.csv").write_text(
        "data", encoding="utf-8")
    _write_inventory(
        tmp_path,
        "csv/SR1_M87_2017_095_hi_hops_netcal_StokesI.csv\n")
    tree = build_tree(tmp_path, sample_fmt)
    assert len(tree["data"]) == 1

def test_build_tree_each_stem_has_correct_columns(sample_tree):
    for stem, pf in sample_tree["data"].items():
        assert set(pf.columns) == {"path", "ext", "year", "day", "band"}, \
                                  f"{stem} has incorrect columns: {pf.columns}"

def test_build_tree_each_stem_has_all_three_formats(sample_tree):
    for stem, pf in sample_tree["data"].items():
        assert set(pf["ext"].unique()) == {"csv", "txt", "uvfits"}, (
            f"{stem} has wrong formats: {set(pf['ext'].unique())}")

### fmt variations tests ###

# needs unique dataset to test for nested subdirectory handling
def test_build_tree_nested_subdir_fmt(tmp_path):
    (tmp_path / "casa_data" / "April05").mkdir(parents=True)
    (tmp_path / "hops_data" / "April05").mkdir(parents=True)
    (tmp_path / "casa_data" / "April05" / "SR2_M87_2017_095_hi_casa.uvfits").write_text(
        "data", encoding="utf-8")
    (tmp_path / "hops_data" / "April05" / "SR2_M87_2017_095_hi_hops.uvfits").write_text(
        "data", encoding="utf-8")
    _write_inventory(
        tmp_path,
        "casa_data/April05/SR2_M87_2017_095_hi_casa.uvfits\n"
        "hops_data/April05/SR2_M87_2017_095_hi_hops.uvfits\n")
    fmt = "{pipeline}_data/{date}/SR2_M87_{year}_{day}_{band}_{pipeline}.uvfits"
    tree = build_tree(tmp_path, fmt)
    assert len(tree["data"]) == 2


# validation test
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