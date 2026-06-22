# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0

"""Take the commentary out of a scaffolded QML file, and leave the licence on.

The command line and the editor scaffold the same files, and they are read in two very
different situations. ``synqt add entity`` is answered in a terminal, and its file is the
only explanation of what the entity is for; the comments in it are the documentation, which
is why they are there. The editor is a drawing of the system with a panel down one side that
already says what every kind of entity is, so the same paragraphs arrive a second time, in a
pane, beside a picture that made the point first. A file somebody dragged into being should
be the shortest true version of itself.

So the templates keep their comments and the editor takes them off, rather than the two
growing a second set of templates that would have to be kept in step with the first.

The SPDX header stays, always. Every SynQt source file carries one (see CONTRIBUTING.md),
and a scaffolder that wrote a file without one would be writing a file that fails the
project's own checks the moment it lands.

``assets/design/commentary.js`` is the same function on the browser side, for the copy of the
editor that has no Python behind it; ``test_qmlcomments.py`` runs both over the same inputs
and fails when they disagree.
"""

from __future__ import annotations

import re
from typing import List

#: The two lines that are never commentary. Matched on the tag rather than the whole line so
#: a project that changes the copyright holder keeps its header.
_LICENCE = re.compile(r"^\s*//\s*SPDX-(FileCopyrightText|License-Identifier):")

_QUOTES = ("\"", "'", "`")


def _cut_trailing(line: str) -> str:
    """`line` up to the first `//` that is not inside a string literal.

    Quote-aware because a scaffold can hold a web address, and cutting at the first `//`
    inside one of those would leave an unterminated string: a file that no longer parses
    is a worse outcome than a comment nobody wanted.
    """
    quote = ""
    index = 0
    while index < len(line):
        character = line[index]
        if quote:
            if character == "\\":
                index += 2
                continue
            if character == quote:
                quote = ""
        elif character in _QUOTES:
            quote = character
        elif character == "/" and line[index + 1:index + 2] == "/":
            return line[:index]
        index += 1
    return line


def without_commentary(text: str) -> str:
    """`text` with every comment gone but the licence header, and no gap left where one was.

    A whole-line comment takes its line with it; a trailing one is cut off the end of the
    code it followed. Runs of blank lines are collapsed to one, because a paragraph removed
    from between two functions otherwise leaves the hole it was written in.
    """
    kept: List[str] = []
    for line in text.split("\n"):
        if _LICENCE.match(line):
            kept.append(line)
            continue
        if line.lstrip().startswith("//"):
            continue
        trimmed = _cut_trailing(line).rstrip()
        # A line that was only trailing comment and whitespace becomes blank rather than a
        # line of spaces, which is what the blank-run collapse below is written against.
        kept.append(trimmed if trimmed or not line.strip() else "")

    tidied: List[str] = []
    for line in kept:
        if not line.strip() and tidied and not tidied[-1].strip():
            continue
        tidied.append(line)
    while tidied and not tidied[-1].strip():
        tidied.pop()
    return "\n".join(tidied) + "\n" if tidied else ""
