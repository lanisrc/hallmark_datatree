# Copyright 2025 the Hallmark Authors
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


from __future__ import annotations

from pathlib import Path
from typing import Union


class Worktree(type(Path())):
    """Materialized data root used by indexing and consumer tools.

    ``Worktree`` is where file objects are discovered by format string
    and later consumed by downstream software.
    """

    def __new__(cls, path: Union[Path, str]) -> "Worktree":
        path = Path(path).resolve()
        if path.is_dir():
            return super().__new__(cls, path)
        elif path.exists():
            raise FileNotFoundError(f'Worktree "{path}" is not a directory')
        else:
            raise FileNotFoundError(f'Worktree "{path}" not found')

    @classmethod
    def init(cls, path: Union[Path, str]) -> "Worktree":
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return cls(path)

    def __truediv__(self, key):
        return Path(self) / key
