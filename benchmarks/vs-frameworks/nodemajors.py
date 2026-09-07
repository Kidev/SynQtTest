# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0

"""Which Node majors the comparison measures, read from the file the harness reads.

Node is the one runtime with more than one column, because "how fast is Node" has two
honest answers: the active LTS a team is allowed to deploy, and the current release. Both
are measured, and every Node stack id carries the major that produced it (`node24-bare`,
`node26-bare`), so the two never land on one row.

The list lives in node/runtimes.txt and is read here rather than copied, because it moves
about twice a year: a hand-copied order would quietly file a newly added major at the end
of the table under "a stack this script did not expect", next to the columns that genuinely
are unexpected.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

RUNTIMES = Path(__file__).resolve().parent / "node" / "runtimes.txt"


def node_majors() -> List[str]:
    """The majors, in the order the file lists them. Empty if it cannot be read.

    Empty rather than a built-in fallback: a fallback would be a second copy of the list,
    which is the thing this function exists to avoid. With an empty list the Node columns
    simply print after the ordered ones instead of among them, which is a cosmetic loss and
    not a wrong number.
    """
    try:
        lines = RUNTIMES.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [major for major in (line.split("#", 1)[0].strip() for line in lines) if major]
