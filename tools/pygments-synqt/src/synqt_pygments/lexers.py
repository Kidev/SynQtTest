# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0
"""Pygments lexers used by the SynQt docs.

SynLexer highlights `.syn` contract files (the `contract`/`record` surface over
QtRO rep files, see docs/programming-model.md). CliLexer highlights the `synqt`
CLI reference listings (command, placeholders, flags, and a trailing `#`
description), used for the long command tables in docs/build-system-and-cli.md
and docs/providers.md so a command reads apart from its description at a
glance, the same job a shell prompt/comment split does for real shell examples.

SynqtQmlLexer highlights the QML code blocks. It extends Pygments' stock QmlLexer
so a SynQt attached signal handler, `Contract.onSignal:` (see the "Handling a
connect point's signals" section of docs/programming-model.md), colors the
contract type and the handler separately instead of as one keyword blob. The
docs map the `qml` fence to it via `extend_pygments_lang` in mkdocs.yml, so
````qml` blocks match the hand-authored home page tooltip.
"""

from pygments.lexer import RegexLexer, bygroups, default, inherit, words
from pygments.lexers.data import YamlLexer
from pygments.lexers.webmisc import QmlLexer
from pygments.token import (Comment, Keyword, Name, Number, Operator, Punctuation,
                            Text, Whitespace)

__all__ = ["SynLexer", "CliLexer", "SynqtQmlLexer", "SynqtYamlLexer"]


class SynLexer(RegexLexer):
    """Lexer for SynQt contract members: a `.syn` file, and the `export:` block of a
    connect point in `synqt.yaml`, which is the same language written on the point.

    Four things are colored apart, because four things is what a member line says: what
    kind of member it is (`prop`, `model`, `signal`, `slot`), what type each value is,
    how wide that type is allowed to be (`string[80]`), and what everything is called.
    The width is the one most worth seeing: it is a rule the owner keeps at the boundary,
    not a comment about the intended size, and a reader skimming a contract should be able
    to find every one of them without reading the line.
    """

    name = "SynQt Contract"
    aliases = ["syn", "synqt-contract"]
    filenames = ["*.syn"]
    mimetypes = ["text/x-synqt-contract"]

    keywords = ("contract", "record")
    member_kinds = ("prop", "model", "signal", "slot")
    # QML's own value types, which is the whole vocabulary a contract may name (see
    # docs/programming-model.md); there is no int16 and no float32 to write.
    builtin_types = ("int", "string", "bool", "real", "float", "double", "var", "url",
                     "date", "color", "point", "size", "rect")

    # Tokens of their own rather than the stock `Keyword.Type` and `Number.Integer`,
    # for the same reason the runtime accessors have one: Pygments writes an unknown
    # leaf as its own CSS class (`kt-Contract`, `mi-Width`), so the docs can color a
    # contract's types and widths without touching the class every other code block on
    # the site shares. Material paints `.k` and `.kt` the same, so without this a
    # member's kind and its type are one color and the line says less than it holds.
    contract_type = Keyword.Type.Contract
    width = Number.Integer.Width

    # A type with the width it is allowed to carry: the brackets and the number are their
    # own tokens, so the width can be colored as the boundary check it is.
    sized_type = (r"\b([A-Za-z_]\w*)(\[)(\d+)(\])",
                  bygroups(contract_type, Punctuation, width, Punctuation))
    plain_type = (words(builtin_types, prefix=r"\b", suffix=r"\b"), contract_type)
    # A capitalized identifier is a contract or record type, whether it is being declared
    # (`contract Todo`) or referenced as a parameter or return type
    # (`slot insert(ItemRow row)`).
    named_type = (r"[A-Z][A-Za-z0-9_]*", Name.Class)

    tokens = {
        "root": [
            (r"//.*$", Comment.Single),
            (r"\s+", Whitespace),
            (r"[{}()]", Punctuation),
            (r",", Punctuation),
            (words(keywords, suffix=r"\b"), Keyword),
            # Each member kind hands over to a state that reads the type (if the kind has
            # one) and then the member's own name, so a name is colored as a name wherever
            # it sits on the line rather than by how far along it is.
            (r"\b(prop)\b", Keyword, "member"),
            (r"\b(model|signal)\b", Keyword, "member"),
            (r"\b(slot)\b", Keyword, "member"),
            sized_type,
            plain_type,
            named_type,
            (r"[a-z_][A-Za-z0-9_]*", Name.Variable),
            (r".", Text),
        ],
        # Between a member kind and the member's own name: any number of type tokens (none
        # for a signal, one for a prop, one or none for a slot), then the name.
        "member": [
            (r"[ \t]+", Whitespace),
            sized_type,
            plain_type,
            named_type,
            (r"[a-z_][A-Za-z0-9_]*", Name.Function, "#pop"),
            default("#pop"),
        ],
    }


class SynqtQmlLexer(QmlLexer):
    """QML lexer that colors type names, and understands SynQt's attached handlers.

    Three things the stock QmlLexer gets wrong for these docs.

    A named type falls through to the JavaScript lexer's catch-all identifier
    rule, so it arrives as plain text: the one word that says what an object *is*
    looks like every local variable around it. That covers both places a type
    appears, the object being declared (`ApplicationWindow {`) and the object
    being addressed from a script (`Caller.hasScope(...)`, `Database.access`,
    `Server.feed.rows`). It is the same thing `contract Feed` names in a `.syn`
    file, so it gets the same token, `Name.Class`, and therefore the same color.

    Within those type names, the framework's own accessors (`Server`, `Session`,
    `Router`, `App`, `Caller`, `Client`, the table at the top of
    docs/runtime-api.md) are not types at all: nothing declares them, nothing
    imports them, and one of them exists only inside an owner's slot. They are what
    SynQt hands you, so they get a color of their own rather than the one that says
    "a type, and somewhere there is a file defining it".

    And any `identifier.chain:` binding is matched as a single Keyword token, so
    `Auth.onLoginFailed:` colors as one blob and the contract type is lost.
    Splitting the leading `Type.` from the `on<Signal>:` handler restores it. A
    plain handler like `onClicked:` has no `Type.` prefix and still falls through
    to the inherited rule, so nothing else changes.
    """

    name = "SynQt QML"
    aliases = ["synqt-qml"]
    filenames = []
    mimetypes = []

    # The JavaScript globals, which the inherited lexer already marks as built-ins and
    # colors as such. They are addressed exactly like a QML type (`Math.hypot(...)`), so
    # the qualifier rule below has to step over them by name or it would take the
    # language's own objects and the ones this project declares and paint them alike.
    javascript_globals = (
        "Array", "ArrayBuffer", "Boolean", "Date", "Error", "EvalError", "Function",
        "Infinity", "Intl", "JSON", "Map", "Math", "NaN", "Number", "Object", "Promise",
        "Proxy", "RangeError", "ReferenceError", "Reflect", "RegExp", "Set", "String",
        "Symbol", "SyntaxError", "TypeError", "URIError", "WeakMap", "WeakSet",
    )

    # The accessors the framework injects, the full list from the table at the top of
    # docs/runtime-api.md. They are matched as whole words, so a project type whose name
    # merely starts or ends with one of them (`SessionSource`, `SynClient`) is untouched
    # and stays an ordinary type.
    runtime_accessors = ("App", "Caller", "Client", "Router", "Server", "Session")

    tokens = {
        "root": [
            # A module name, so the qualifier rule below leaves it alone: `QtQuick` and
            # `QtQuick.Controls` are the same kind of thing and must look it, and a dotted
            # module name is not an object being addressed.
            (r"(import|pragma)([ \t]+)([\w.]+)",
             bygroups(Keyword.Reserved, Whitespace, Name.Other)),
            # An accessor, before every rule that would otherwise claim it as a type. It
            # is matched wherever it appears rather than only before a dot, because the
            # point is the name itself: `Caller` is the same object whether it is being
            # asked a question or handed to something.
            (words(runtime_accessors, prefix=r"\b", suffix=r"\b"), Name.Builtin.Accessor),
            # A type being instantiated: the name immediately before the brace that
            # opens the object, `ApplicationWindow {` or `QtObject {`, optionally
            # qualified (`Qt.labs.settings.Settings {`). The brace must be on the
            # same line, which is how QML is written throughout these docs and what
            # keeps the rule from reaching across a line to an unrelated block.
            (r"([A-Z]\w*(?:\.[A-Z]\w*)*)([ \t]*)(\{)",
             bygroups(Name.Class, Whitespace, Punctuation)),
            # `Behavior on width { ... }`: the same declaration with the property it
            # animates wedged into the middle of it.
            (r"(Behavior)(\s+)(on)(\s+)(\w+)([ \t]*)(\{)",
             bygroups(Name.Class, Whitespace, Keyword, Whitespace, Name, Whitespace,
                      Punctuation)),
            # An attached signal handler: SynQt's `Auth.onLoginFailed:`, and QML's own
            # `Component.onCompleted:`. Split the type from the handler so the type is
            # not swallowed into the binding keyword.
            (r"([A-Z]\w*)(\.)(on[A-Z]\w*\s*:)", bygroups(Name.Class, Punctuation, Keyword)),
            # A type being addressed rather than declared: whatever stands to the left of
            # the dot in `Caller.hasScope(...)`, `Server.feed.rows`, `Layout.fillWidth:`,
            # or `Text.WordWrap`. Only the head of the chain is a name you could have
            # written a type for; everything past the first dot is a member of it, and
            # stays plain so the eye lands on the thing being named.
            (r"(?!(?:%s)\b)[A-Z]\w*(?=\.)" % "|".join(javascript_globals), Name.Class),
            # An arrow reads as one operator, not `=` then `>`.
            (r"=>", Operator),
            inherit,
        ],
    }


class CliLexer(RegexLexer):
    """Lexer for the `synqt` CLI reference listings in the docs."""

    name = "SynQt CLI Reference"
    aliases = ["cli", "synqt-cli"]
    filenames = []
    mimetypes = []

    tokens = {
        "root": [
            (r"#.*$", Comment.Single),
            (r"\s+", Whitespace),
            (r"\.\.\.", Operator),
            (r"\|", Operator),
            (r"[\[\]]", Punctuation),
            (r"<[^>]+>", Name.Variable),
            (r"--?[A-Za-z][\w-]*", Name.Attribute),
            (r"synqt\b", Name.Builtin),
            (r"[A-Za-z][\w-]*", Keyword),
            (r".", Text),
        ],
    }


class SynqtYamlLexer(YamlLexer):
    """YAML that reads a connect point's ``export:`` block as the contract it is.

    A `synqt.yaml` is two languages in one file. Almost all of it is configuration, and
    YAML colors that well enough. The `export:` block on a connect point is not
    configuration at all: it is the contract, the one place a project says what may cross
    a link, and a plain YAML lexer hands the whole thing over as one undifferentiated
    string. Every member, every type, and every width comes out the same color, which is
    the opposite of what the block is for.

    So the block is lexed with :class:`SynLexer`, the same lexer the `.syn` reference
    pages use, and the two read alike wherever they appear. Nothing else in the file
    changes: only the scalar directly under an `export:` key is taken, and it is taken by
    following the key rather than by matching the text, so a value that happens to look
    like a member somewhere else is left alone.
    """

    name = "SynQt YAML"
    aliases = ["synqt-yaml"]
    filenames = []
    mimetypes = []

    def get_tokens_unprocessed(self, text):
        contract = SynLexer()
        inside = False
        for index, token, value in super().get_tokens_unprocessed(text):
            if token is Name.Tag:
                # Any other key ends the block: YAML gives the block scalar's lines back
                # one at a time with no marker for where it stops, and the next key is the
                # first thing that can only appear outside it.
                inside = value.strip() == "export"
                yield index, token, value
                continue
            if inside and token in Name.Constant:
                for offset, kind, part in contract.get_tokens_unprocessed(value):
                    yield index + offset, kind, part
                continue
            yield index, token, value
