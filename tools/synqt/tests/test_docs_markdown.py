# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0

"""No documentation page publishes a list item as literal `- ` text.

Written after the whole resource-limits list on `docs/security.md` shipped that way: seven
bullets on the most safety-relevant page in the site rendered as `- Connection caps.` in
the middle of a paragraph. A list item at the left margin is absorbed into the block above
it when that block is still open, and Markdown says nothing, because the file is valid and
the build is green. `mkdocs build --strict` cannot see it and neither can a link checker,
so the source pattern is the only cheap signal.

The three shapes below are what the renderer actually does, measured against it rather
than reasoned about, and `test_the_shapes_this_was_measured_against` is the record of
that measurement.
"""

import re
import unittest
from pathlib import Path

DOCS = Path(__file__).resolve().parents[3] / "docs"

#: A list item at the left margin. An indented one belongs to a sub-list and is never at
#: risk: what puts an item at risk is the block above it not having been closed.
_ITEM = re.compile(r"^[-*+] \S")


def swallowed_items(text):
    """Every left-margin list item the block above it absorbs, as (line number, text).

    A blank line closes the block, so an item after one always starts a list. Otherwise
    the item is absorbed when the line above it is unindented prose, and when it is an
    indented line belonging to an item that has already been broken by a blank line: that
    item is loose, its second paragraph is still open, and the marker becomes part of it.
    An indented line with no blank since its own marker is an ordinary wrapped line, and
    an item after one starts correctly.
    """
    found = []
    fenced = False
    blank_since_marker = False
    previous = ""
    for number, line in enumerate(text.split("\n"), start=1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            previous = line
            continue
        if fenced:
            previous = line
            continue
        if _ITEM.match(line) and number > 1:
            if previous.strip() and not _ITEM.match(previous):
                indented = previous.startswith((" ", "\t"))
                structural = previous.startswith((">", "|", "<", "#"))
                if not structural and (not indented or blank_since_marker):
                    found.append((number, line[:60]))
        if _ITEM.match(line) or (line.strip() and not line.startswith((" ", "\t"))):
            blank_since_marker = False
        elif not line.strip():
            blank_since_marker = True
        previous = line
    return found


class DocsMarkdownTest(unittest.TestCase):
    def test_no_list_item_is_swallowed_by_the_block_above_it(self):
        offenders = {}
        for page in sorted(DOCS.glob("*.md")):
            found = swallowed_items(page.read_text(encoding="utf-8"))
            if found:
                offenders[page.name] = found
        self.assertFalse(
            offenders,
            "these list items publish as literal text; put a blank line above each:\n"
            + "\n".join(f"  {name}:{number}: {text}"
                        for name, items in offenders.items()
                        for number, text in items))

    def test_the_shapes_this_was_measured_against(self):
        """What the renderer does with each shape, so a rewrite of the matcher above
        cannot quietly stop looking for the one that shipped."""
        broken = [
            "- First item\n\n  A second paragraph.\n- Second item\n",
            "- First item\n\n    A second paragraph.\n- Second item\n",
            "A paragraph.\n- An item\n",
        ]
        fine = [
            "- First item that wraps\n  onto a second line\n- Second item\n",
            "- First item\n\n    A second paragraph.\n\n- Second item\n",
            "- First item\n\n  A second paragraph.\n\n- Second item\n",
            "```\nA line.\n- not a list\n```\n",
        ]
        for source in broken:
            self.assertTrue(swallowed_items(source), f"missed: {source!r}")
        for source in fine:
            self.assertFalse(swallowed_items(source), f"false alarm: {source!r}")


if __name__ == "__main__":
    unittest.main()
