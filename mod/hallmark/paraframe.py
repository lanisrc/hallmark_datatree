# Copyright 2019 Chi-kwan Chan
# Copyright 2019 Steward Observatory
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

from glob import glob
from pathlib import Path

import re
import parse
import pandas as pd
import numpy as np

from .helper_functions import find_spec_by_fmt, regex_sub, try_numeric_conversion


class ParaFrame(pd.DataFrame):
    """
    A subclass of :class:`pandas.DataFrame` with added methods for
    parameterized file discovery and filtering.

    ``ParaFrame`` instances behave like ordinary DataFrames but add:


    * ``__init__``: Initialises the class and stores ``encodings`` and 
      ``base_path`` as metadata
        to the ParaFrame. 
    * ``_constructor``: Returns the subclassed ParaFrame with repo_path as a
        default keyword argument.
    * ``glob_search'': Returns files found in the directory using format string.
    * ``parse``: a classmethod that builds a table of file paths and parsed
        parameters from a format pattern (using ``glob`` + ``parse``).
    * ``__call__``/``filter``: convenience filtering by column values.
    """

    _metadata = ["encodings", "base_path"]

    def __init__(self, data=None, encodings=None, base_path=None, **kwargs):
        super().__init__(data, **kwargs)
        self.encodings = encodings or {}
        self.base_path = Path(base_path) if base_path is not None else Path.cwd()

    @property
    def _constructor(self):
        def _c(*args, **kwargs):
            kwargs.setdefault("encodings", self.encodings)
            kwargs.setdefault("base_path", self.base_path)
            return ParaFrame(*args, **kwargs)
        return _c

    def __call__(self, **kwds):
        return self.filter(**kwds)

    def filter(self, **kwargs):
        """
        Filter a pandas ``DataFrame`` by matching column values.

        This function utlizes provided **kwargs to filter an existing
        ``ParaFrame`` by masking based on column values. Filtering supports
        single- and multi-conditioned queries, returning rows that satisfy
        any of the provided conditions.

        Args:
        **kwargs: Arbitrary keyword arguments specifying column names
             and values to filter by.
        * If the value is a tuple or list, rows where the column
               matches any of those values are selected.
        * If the value is a scalar, rows where the column equals
               the value are selected.

        Returns:
         pandas.DataFrame: A filtered DataFrame containing only rows
             that match the given conditions.
        """
        mask = np.zeros(len(self), dtype=bool)
        for k, v in kwargs.items():
            if isinstance(v, (tuple, list)):  # looking through the specified conditions
                mask |= np.isin(np.array(self[k]), np.array(v))
            else:
                mask |= np.array(self[k]) == v
        return self[mask]

    @classmethod
    def glob_search(
        cls,
        fmt,
        *args,
        encodings=None,
        base_path=None,
        debug=False,
        return_pattern=False,
        encoding=False,
        **kwargs,
    ):
        """
        Find all the files specified in a directory using the format string specified.

        This function utilizes the provided format string to find the specified
        files. This function also looks through .yaml files if encoding = True
        and evaluates conditionals.

        Args:
        fmt (str): A format string specifying the expected file naming
            pattern.
            Fields wrapped in ``{}`` will be extracted into columns.
        *args: Positional arguments used to fill the format string.
        encodings (dict):   The ``encodings`` list from ``State``
            (contents of ``config.yml``).
            Defaults to ``{}``.
        base_path (Path):   Root directory to search from.
            Defaults to ``Path.cwd()``.
        debug (bool, optional): If True, prints debugging information
            about the matching process.
            Defaults to False.
        return_pattern (bool, optional): Returns the pattern and globbed files.
            Defaults to False.
        encodings (bool,optional): If True, looks for the .yaml file and
            extracts user specified format information.
            Defaults to False.
        **kwargs: Keyword arguments used to fill the format string.
            If missing keys are encountered, they will be replaced by
            a wildcard ``*`` for globbing.

        Returns:
         if return_pattern = True, it returns the pattern and the globbed files.
         Else, it returns the globbed files, the format string with the wildcards
         and the user specification in the .yaml file (None, if encoding = False).
        """
        encodings = encodings or {}
        base_path = Path(base_path) if base_path is not None else Path.cwd()

        pmax = len(fmt) // 3  # to specify a parameter, we need at least
        # three characters '{p}'; the maximum number
        # of possible parameters is `len(fmt) // 3`.

        fmt_enc = fmt
        enc_dict = {}
        needs_encoding = None

        if encoding:
            for entry in encodings:
                if entry.get("fmt") in fmt:
                    fmt_enc = entry["fmt"]
                    break

            yaml_encodings = find_spec_by_fmt(fmt_enc, encodings)

            # Conditionals checking .yaml file and user specifications are consistent.
            if yaml_encodings is None:
                raise ValueError(
                    f"Error: The format '{fmt_enc}' is missing from hallmark.yml."
                )

            enc_dict = yaml_encodings.get("encoding", {})
            needs_encoding = any(v != "" for v in enc_dict.values())
            if not needs_encoding and encoding:
                raise ValueError(
                    f"'{fmt_enc}' has no regex spec; use encoding=False."
                )
        else:
            yaml_encodings = {}

        if needs_encoding is not None and not encoding:
            raise ValueError(
                f"'{fmt_enc}' has a regex spec; use encoding=True."
            )

        # pattern = base + fmt
        pattern = str(base_path / fmt.lstrip("/"))
        fmt_g = fmt_enc.lstrip("/")
        
        for i in range(pmax):
            if debug:
                print(i, pattern, args, kwargs)
            try:
                pattern = pattern.format(*args, **kwargs)
                break
            except KeyError as e:
                k = e.args[0]
                pattern = re.sub(r"\{" + k + r":?.*?\}", "{" + k + "}", pattern)
                fmt_g = re.sub(r"\{" + k + r":?.*?\}", "{" + k + "}", fmt_g)
                kwargs[k] = "*"

        # Obtain list of files based on the glob pattern
        globbed_files = sorted(glob(pattern))

        # Print the glob pattern and a summary of matches
        if debug:
            print(f'Pattern: "{pattern}"')
            n = len(globbed_files)
            if n > 1:
                print(f'{n} matches, e.g., "{globbed_files[0]}"')
            elif n > 0:
                print(f'{n} match, i.e., "{globbed_files[0]}"')
            else:
                print("No match; please check format string")

        if return_pattern:
            return (globbed_files, pattern)
        else:
            return (yaml_encodings, fmt_g, globbed_files)

    @classmethod
    def parse(
        cls,
        fmt,
        *args,
        encodings=None,
        base_path=None,
        debug=False,
        encoding=False,
        **kwargs,
    ):
        """Build a ``ParaFrame`` by parsing file paths that match a pattern.

        Args:
            fmt (str):        Format string with ``{param}`` fields.
            encodings (dict): The ``encodings`` dict from ``State``
                              (contents of ``hallmark.yml``).
                              Defaults to ``{}``.
            base_path (Path): Root directory to search from.
                              Defaults to ``Path.cwd()``.
            debug (bool):     Print debug info. Defaults to ``False``.
            encoding (bool):  Apply regex encoding. Defaults to ``False``.

        Returns:
            ``ParaFrame`` where each row is a matched file with parsed
            parameters as columns, plus a ``path`` column.

        Example:
            >>> from hallmark import ParaFrame
            >>> pf = ParaFrame.parse(
            ...     "/custom_parameter{custom_parameter}_p{parameter}.h5",
            ...     encoding=True
            ... )
        """
        base_path = Path(base_path) if base_path is not None else Path.cwd()

        yaml_encodings, fmt_g, globbed_files = cls.glob_search(
            fmt, *args,
            encodings=encodings,
            base_path=base_path,
            debug=debug,
            encoding=encoding,
            **kwargs,
        )

        parser = parse.compile(fmt_g)
        frame = []

        # Writing the ParaFrame
        for f in globbed_files:
            f_short = str(Path(f).relative_to(base_path))
            if encoding:
                f_new = regex_sub(f_short, yaml_encodings)
            else:
                f_new = f_short

            r = parser.parse(f_new)

            if r is None:
                print(f'Failed to parse "{f}"')
            else:
                frame.append({"path": f_short, **r.named})
        # attempt to convert each parameter column to numeric
        # if conversion fails the column stays as string
        result = cls(frame, encodings=encodings, base_path=base_path)
        for col in result.columns:
            result[col] = try_numeric_conversion(result[col])
        return result
