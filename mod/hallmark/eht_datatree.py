from __future__ import annotations
from pathlib import Path
from hallmark import ParaFrame
import parse

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
    # add files to missing if not in tracked but in inventory
    missing = [file for file in files_list if file not in tracked]
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
    
# common drive extensions to look for when building the tree
DRIVE_EXTENSIONS = [".tgz", ".tar", ".gz", ".zip", ".bz2", ".xz", ".zst", ".7z", ".rar"]

def build_tree(root: Path, fmt: str) -> dict:
    """
    Build an in-memory pytree for an EHT dataset directory.

    Args:
        root: Path to the EHT dataset root directory.
        fmt: Format string for parsing data files.

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
    # collect all drive paths matching any supported extension
    drive_paths = []
    for ext in DRIVE_EXTENSIONS:
        # add any file that has this ext to the drive paths list and tracked set
        for path in root.rglob(f"*{ext}"):
            drive_paths.append(str(path.relative_to(root)))
            tracked.add(str(path.relative_to(root)))
    # build a single ParaFrame from all drive paths
    drives_pf = ParaFrame(
        [{"path": path} for path in sorted(drive_paths)],
        base_path=root,
    )

    ### DATA ###
    # find all files that are named using the provided format string
    globbed_files, _ = ParaFrame.glob_search(fmt, base_path=root, return_pattern=True)
    # turn the fmt into a parser to extract fields from file paths
    parser = parse.compile(fmt)
    stems = {}
    for file in globbed_files:
        # get path to file from data root
        relative_path = str(Path(file).relative_to(root))
        # parse the path to extract fields, skip if it doesn't match the format
        parsed = parser.parse(relative_path)
        if parsed:
            # create unique stem name based on fmt parameters excluding extension
            stem_key = "_".join(str(value) for key, value in parsed.named.items() 
                                if key != "ext")
            # create stem if it doesn't already exist and add a row for this file
            stems.setdefault(stem_key, []).append(
                {"path": relative_path,
                 "ext": Path(relative_path).suffix,
                 **parsed.named}
            )
            tracked.add(relative_path)

    data_branches = {}
    # create a ParaFrame for each stem and add to the data branches dict
    for stem_key, rows in stems.items():
        data_branches[stem_key] = ParaFrame(rows, base_path=root)

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
        "data"   : data_branches,
    }