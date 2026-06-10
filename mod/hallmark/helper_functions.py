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

import re


def find_spec_by_fmt(fmt, encodings):
    """Find the encoding spec for a given format string.

    Args:
        fmt:       Format string to look up.
        encodings: The ``encodings`` list from ``State`` (i.e., the contents
                   of ``config.yml``).

    Returns:
        The matching spec dict, or ``None`` if not found.
    """
    for spec in encodings:
        if spec.get("fmt") == fmt:
            return spec
    return None


def regex_sub(value, yaml_encodings):
    """Apply regex substitution defined in an encoding spec.

    Args:
        value:          Format string / file path to transform.
        yaml_encodings: A single encoding spec dict (one entry from the
                        ``data`` list in ``hallmark.yml``), or ``None``.

    Returns:
        The (possibly transformed) format string.
    """
    if yaml_encodings is None:
        return value

    enc = yaml_encodings.get("encoding")
    if not enc:
        return value

    regex = enc.get("aspin", "")
    if not regex:
        return value

    result = value
    for match in re.finditer(regex, value):
        result = re.sub(match.group(0), "-" + str(match.group(1)), result)

    return result
