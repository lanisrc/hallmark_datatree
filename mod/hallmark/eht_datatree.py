from __future__ import annotations
from pathlib import Path
from hallmark import ParaFrame

"""
Read INVENTORY.txt and return expected relative file paths.

    Args:
        root: Path to the dataset root directory containing INVENTORY.txt.

    Returns:
        List of relative file path strings expected to exist under root.

    Raises:
        FileNotFoundError: If INVENTORY.txt does not exist under root.
"""
def read_inventory(root: Path) -> list[str]:
    inventory_path = Path(root) / "INVENTORY.txt"
    if not inventory_path.exists():
        raise FileNotFoundError(f"INVENTORY.txt not found in {root}")

    files_list = []
    # skip directory lines ending in "/" and strip executable marker "*"
    for line in inventory_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.endswith("/"):
            continue
        line = line.rstrip("*")
        files_list.append(line)
    return files_list

"""
Cross-check INVENTORY.txt against a set of tracked files in tree.

    Args:
        root:    Path to the dataset root containing INVENTORY.txt.
        tracked: Set of relative file path strings already in the tree.

    Returns:
        True if all inventory files are accounted for, False otherwise.
"""
def validate(root: Path, tracked: set[str]) -> bool:
    files_list = read_inventory(root)
    missing = []
    # Check that every file in the inventory is present in the tracked set
    for f in files_list:
        if f not in tracked:
            missing.append(f)
    if missing:
        print(f"  missing  : {len(missing)} file(s)")
        for f in missing:
            print(f"    ✗  {f}")
        return False
    else:
        print("  ✓ all inventory files are present in the tree")
        return True

"""
Build an in-memory pytree for an EHT dataset directory.

Args:
    root: Path to the EHT dataset root directory.

Returns:
    A dictionary with keys:
        - "meta"   : ParaFrame of housekeeping files
        - "drives" : ParaFrame of compressed archives
        - "data"   : dict of {stem -> ParaFrame}
"""
# hardcoded formats for this dataset, based on inventory and globbing
FMT_DRIVES = "{name}.tgz"
FMT_DATA   = "{ext}/SR1_M87_{year}_{day}_{band}_hops_netcal_StokesI.{ext}"
def build_tree(root: Path) -> dict:

    root = Path(root).expanduser().resolve()
    # track files that are included in the tree, to cross-check against inventory
    tracked = set()

    # drives
    drives_pf = ParaFrame.parse(FMT_DRIVES, base_path=root)
    # drop name column as it is redundant with path
    drives_pf = drives_pf.drop(columns=["name"])
    # adds all files with drive extension to tracked set
    for path in drives_pf["path"]:
        tracked.add(path)

    # data
    all_data_pf = ParaFrame.parse(FMT_DATA, base_path=root)
    # find unique stem combinations to build one branch per observation
    # currently hardcoded with this dataset, will need to be generalized
    stems = all_data_pf[["year", "day", "band"]].drop_duplicates()
    data = {}
    for _, row in stems.iterrows():
        year, day, band = row["year"], row["day"], row["band"]
        branch_name = f"SR1_M87_{year}_{day}_{band}_hops_netcal_StokesI"
        mask = (
            (all_data_pf["year"] == year) &
            (all_data_pf["day"] == day) &
            (all_data_pf["band"] == band)
        )
        stem_pf = all_data_pf[mask]
        data[branch_name] = stem_pf
        for path in stem_pf["path"]:
            tracked.add(path)

    # meta
    all_files = {
        str(f.relative_to(root))
        for f in root.rglob("*")
        if f.is_file() and f not in tracked
    }
    meta_files = all_files - tracked
    # adds all files that weren't in the other branches
    meta_pf = ParaFrame(
        [{"path": f} for f in sorted(meta_files)],
        base_path=root,
    )

    # cross-check against inventory that no files are missing from the tree
    all_tracked = set()
    for _, row in meta_pf.iterrows():
        all_tracked.add(row["path"])
    for _, row in drives_pf.iterrows():
        all_tracked.add(row["path"])
    for pf in data.values():
        for _, row in pf.iterrows():
            all_tracked.add(row["path"])
    validate(root, all_tracked)
        

    return {
        "meta"   : meta_pf,
        "drives" : drives_pf,
        "data"   : data,
    }