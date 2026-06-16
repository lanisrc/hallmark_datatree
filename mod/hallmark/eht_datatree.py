from __future__ import annotations
from pathlib import Path
from hallmark import ParaFrame
import parse

def _strip_suffixes(path: str) -> str:
    """Strip all suffixes from a path string to help with parsing inventory files."""
    p = Path(path)
    while p.suffix:
        p = p.with_suffix("")
    return str(p)

def _alternative_spellings(path: str) -> list[str]:
    """Return alternative spellings for known filename variants."""
    alternatives = [path]
    if "LICENSE" in path:
        alternatives.append(path.replace("LICENSE", "LICENCE"))
    if "LICENCE" in path:
        alternatives.append(path.replace("LICENCE", "LICENSE"))
    return alternatives

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
        # check there is a file extension
        if not Path(line).suffix:
            continue
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
    # checks the end rather than exact match to handle nesting and strip suffixes
    missing = [
    file for file in files_list
    if not any(
        t.endswith(alt) or _strip_suffixes(t).endswith(_strip_suffixes(alt))
        for t in tracked
        # catch issues like licence/license
        for alt in _alternative_spellings(file))]
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

def build_tree(root: Path, fmt: str | list[str]) -> dict:
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
    # build a single ParaFrame from all drive paths with extensions column
    drives_pf = ParaFrame(
    [{"path": path, "ext": Path(path).suffix.lstrip(".")} 
     for path in sorted(drive_paths)],
    base_path=root,)

    ### DATA ###
    # check if there is only one fmt
    fmts = [fmt] if isinstance(fmt, str) else fmt
    # make a parser for each fmt
    parsers = [parse.compile(f) for f in fmts]
    stems = {}
    # search all subdirectories from root
    for file in root.rglob("*"):
        # if the file isn't a folder
        if not file.is_file():
            continue
        # reset parse for each file
        parsed = None
        # parse the path to extract fields, skip if it doesn't match the format
        for parser in parsers:
            parsed = (parser.parse(file.name) or 
                      parser.parse(file.stem) or 
                      parser.parse(file.stem.split(".")[0]))
            # break out once matching parser found
            if parsed:
                break
        if parsed:
            # get path to file from data root
            relative_path = str(file.relative_to(root))
            # create unique stem name based on fmt parameters excluding extension
            stem_key = "_".join(str(value) for key, value in parsed.named.items() 
                                if key != "ext")
            # create stem if it doesn't already exist and add a row for this file
            stems.setdefault(stem_key, []).append(
                {"path": relative_path,
                 # normalize ext to not have period
                 "ext": Path(relative_path).suffix.lstrip("."),               
                 **{key: value for key, value in parsed.named.items() if key != "ext"},}
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
    # create a paraframe for the meta files with extensions column
    meta_pf = ParaFrame(
    [{"path": file, "ext": Path(file).suffix.lstrip(".")} 
     for file in sorted(meta_files)],
    base_path=root,)
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