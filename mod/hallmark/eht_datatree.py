from __future__ import annotations
from pathlib import Path
from hallmark import ParaFrame

def read_inventory(root: Path) -> list[str]:
    """
    Read INVENTORY.txt and return expected relative file paths.

        Args:
            root: Path to the dataset root directory containing INVENTORY.txt.

        Returns:
            List of relative file path strings expected to exist under root.

        Raises:
            FileNotFoundError: If INVENTORY.txt does not exist under root.
    """
    # finds path to the inventory file, raises error if not found
    inventory_path = Path(root) / "INVENTORY.txt"
    if not inventory_path.exists():
        raise FileNotFoundError(f"INVENTORY.txt not found in {root}")

    files_list = []
    # skip directory lines ending in "/" and strip executable marker "*"
    for line in inventory_path.read_text(encoding="utf-8").splitlines():
        # remove whitespace
        line = line.strip()
        # skip empty lines and directories
        if not line or line.endswith("/"):
            continue
        # remove executable marker if present
        line = line.rstrip("*")
        # add cleaned line to files list
        files_list.append(line)
    return files_list

def validate(root: Path, tracked: set[str]) -> bool:
    """
    Cross-check INVENTORY.txt against a set of tracked files in tree.

        Args:
            root:    Path to the dataset root containing INVENTORY.txt.
            tracked: Set of relative file path strings already in the tree.

        Returns:
            True if all inventory files are accounted for, False otherwise.
    """
    files_list = read_inventory(root)
    missing = []
    # Check that every file in the inventory is present in the tracked set
    for file in files_list:
        if file not in tracked:
            # add file not in tracked to missing list
            missing.append(file)
    # if the missing list is not empty, print missing files message
    if missing:
        # print how many files are missing and list them
        print(f"  missing  : {len(missing)} file(s)")
        for file in missing:
            print(f"    ✗  {file}")
        return False
    else:
        print("  ✓ all inventory files are present in the tree")
        return True
    
# hardcoded formats for this dataset, based on inventory and globbing
FMT_DRIVES = "{name}.tgz"
FMT_DATA   = "{ext}/SR1_M87_{year}_{day}_{band}_hops_netcal_StokesI.{ext}"
def build_tree(root: Path) -> dict:
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
    # create clean root path
    root = Path(root).expanduser().resolve()
    # track files that are included in the tree, to cross-check against inventory
    tracked = set()

    ### DRIVES ###
    # create ParaFrame for drive files based on FMT_DRIVES
    drives_pf = ParaFrame.parse(FMT_DRIVES, base_path=root)
    # drop name column as it is redundant with path
    drives_pf = drives_pf.drop(columns=["name"])
    # adds all files with drive extension to tracked set
    for path in drives_pf["path"]:
        tracked.add(path)

    ### DATA ###
    # create ParaFrame for all data files based on FMT_DATA
    all_data_pf = ParaFrame.parse(FMT_DATA, base_path=root)
    # find unique stem combinations to build one branch per observation
    # currently hardcoded with this dataset, will need to be generalized
    stems = all_data_pf[["year", "day", "band"]].drop_duplicates()
    data = {}
    # create a branch for each unique stem combination and add to tree
    for _, row in stems.iterrows():
        year, day, band = row["year"], row["day"], row["band"]
        # harcoded branch name format that will need to be generalized
        branch_name = f"SR1_M87_{year}_{day}_{band}_hops_netcal_StokesI"
        # filter all_data_pf to only rows matching this stem combination
        mask = (
            (all_data_pf["year"] == year) &
            (all_data_pf["day"] == day) &
            (all_data_pf["band"] == band)
        )
        # apply the mask to get only the 3 files for this stem combination
        stem_pf = all_data_pf[mask]
        # store the stem ParaFrame in the data dict under the stem name
        data[branch_name] = stem_pf
        # adds all files in this stem to tracked set
        for path in stem_pf["path"]:
            tracked.add(path)

    ### META ###
    # create a list of all files under root that aren't tracked
    meta_files = {
        str(file.relative_to(root))
        for file in root.rglob("*")
        # add file if its not a dir, not the .hm, and not in tracked
        if file.is_file() 
           and ".hm" not in file.parts
           and str(file.relative_to(root)) not in tracked
    }
    # create a paraframe for the meta files
    meta_pf = ParaFrame(
        [{"path": file} for file in sorted(meta_files)],
        base_path=root,
    )
    for _, row in meta_pf.iterrows():
        tracked.add(row["path"])
        
    # check all files are in the tree
    validate(root, tracked)
        
    # return dict with three keys, only data has subbranches
    return {
        "meta"   : meta_pf,
        "drives" : drives_pf,
        "data"   : data,
    }