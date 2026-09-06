# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0

"""`.dev-identities`: the named people a developer signs in as, over and over.

The scope picker (`synqt dev --identity-picker`) offers the project's declared scopes. That
covers "let me be an admin for a minute"; it does not cover "let me be Alice again", which is
what a developer working on anything keyed to a person actually does. This file is that list:

.. code-block:: yaml

    - email: alice@example.com
      scope: admin
    - email: bob@example.com
      scope: user

It is read here rather than in the edge, and that is the decision worth writing down. The
edge has no YAML parser and should not grow one for a development convenience; this side
already has one, already holds the parsed `synqt.yaml`, and therefore already knows which
scopes the project declares. So `synqt dev` reads the file, keeps the entries that make
sense, and passes them to the edge as ordinary command-line values. Nothing about the file's
format reaches C++.

A bad entry is dropped and reported; it never stops the picker. A typo in a developer's
convenience file taking the whole development sign-in down would be a worse failure than the
typo, and the report is carried through to the picker's own page (`--dev-identity-problem`)
so it is read where the missing name is noticed, not only in the terminal that started the
edge an hour ago.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import yaml

FILE_NAME = ".dev-identities"

#: An entry, as the edge takes it: `<scope>=<email>`. Scope first, because a scope name is a
#: bare identifier and an address is not, so the first `=` is unambiguously the separator.
Entry = Tuple[str, str]


def path_of(project_dir: os.PathLike[str] | str) -> Path:
    return Path(project_dir) / FILE_NAME


def read(project_dir: os.PathLike[str] | str,
         scope_order: Sequence[str]) -> Tuple[List[Entry], List[str]]:
    """Return the usable entries and, separately, one sentence per entry that was dropped.

    Every refusal names the entry, so a developer who does not see Alice in the picker can
    tell which line to fix without reading this function.
    """
    file = path_of(project_dir)
    if not file.exists():
        return [], []

    try:
        document = yaml.safe_load(file.read_text()) or []
    except yaml.YAMLError as error:
        # One message for the whole file: after a parse error there are no entries to
        # attribute anything to.
        return [], [f"{FILE_NAME} is not valid YAML and was ignored entirely: {error}"]

    if not isinstance(document, list):
        return [], [f"{FILE_NAME} must be a list of entries, and this one is a "
                    f"{type(document).__name__}; the whole file was ignored"]

    entries: List[Entry] = []
    problems: List[str] = []
    for index, item in enumerate(document, start=1):
        problem = _problem_with(index, item, scope_order)
        if problem:
            problems.append(problem)
            continue
        entries.append((str(item["scope"]), str(item["email"])))
    return entries, problems


def _problem_with(index: int, item: Any, scope_order: Sequence[str]) -> str:
    where = f"{FILE_NAME} entry {index}"
    if not isinstance(item, dict):
        return f"{where} is a {type(item).__name__}, not an email/scope pair; ignored"

    email = item.get("email")
    scope = item.get("scope")
    if not isinstance(email, str) or not email.strip():
        return f"{where} names no email; ignored"
    if not isinstance(scope, str) or not scope.strip():
        return f"{where} ({email}) names no scope; ignored"

    # The address becomes a command-line value, part of a synthesized identity, and text on
    # the picker's page. The page escapes it, but a value carrying a newline or a control
    # character has no business in any of the three, and refusing it here is one refusal
    # rather than three.
    if any(character.isspace() or ord(character) < 0x20 for character in email):
        return f"{where} ({email!r}) has whitespace or a control character in its email; ignored"

    if scope not in scope_order:
        declared = ", ".join(scope_order) or "none"
        return (f"{where} ({email}) names scope '{scope}', which this project does not "
                f"declare; declared: {declared}. Ignored")
    return ""


def arguments(entries: Sequence[Entry], problems: Sequence[str]) -> List[str]:
    """The flags the edge takes, in the order a reader of the command line would want them."""
    flags: List[str] = []
    for scope, email in entries:
        flags += [f"--dev-identity={scope}={email}"]
    for problem in problems:
        flags += [f"--dev-identity-problem={problem}"]
    return flags


def for_project(project_dir: os.PathLike[str] | str,
                config: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Read the file for one project and return (flags, problems).

    The problems come back as well as going into the flags, because `synqt dev` prints them
    once at startup too: the picker's page is where they are needed, and the terminal is
    where a developer who has not opened the picker yet is looking.
    """
    from . import appmodel  # local: appmodel imports nothing from here, and this keeps it so

    entries, problems = read(project_dir, appmodel.scope_vocab(config))
    return arguments(entries, problems), problems
