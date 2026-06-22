// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

// Take the commentary out of a scaffolded QML file, and leave the licence on.
//
// A file dragged into being should be the shortest true version of itself. The command
// line's scaffolds explain themselves in comments because a terminal has nowhere else to say
// it; this editor is a drawing with a panel down one side that already says what every kind
// of entity is, so the same paragraphs would arrive a second time, in a pane, beside a
// picture that made the point first.
//
// The SPDX header always stays: every SynQt source file carries one, and a scaffolder that
// wrote a file without one would be writing a file that fails the project's own checks the
// moment it lands.
//
// `synqt/qmlcomments.py` is the same function on the Python side, which is what the editor
// uses when there is a CLI behind it. `test_qmlcomments.py` runs both over the same inputs
// and fails when they disagree, so the download and the written project cannot differ.

const LICENCE = /^\s*\/\/\s*SPDX-(FileCopyrightText|License-Identifier):/;

const QUOTES = ["\"", "'", "`"];

// `line` up to the first `//` that is not inside a string literal. Quote-aware because a
// scaffold can hold a web address, and cutting at the first `//` inside one of those
// would leave an unterminated string: a file that no longer parses is a worse outcome
// than a comment nobody wanted.
function cutTrailing(line) {
    let quote = "";
    let index = 0;
    while (index < line.length) {
        const character = line[index];
        if (quote) {
            if (character === "\\") {
                index += 2;
                continue;
            }
            if (character === quote) {
                quote = "";
            }
        } else if (QUOTES.includes(character)) {
            quote = character;
        } else if (character === "/" && line[index + 1] === "/") {
            return line.slice(0, index);
        }
        index += 1;
    }
    return line;
}

// `text` with every comment gone but the licence header, and no gap left where one was.
export function withoutCommentary(text) {
    const kept = [];
    for (const line of String(text || "").split("\n")) {
        if (LICENCE.test(line)) {
            kept.push(line);
            continue;
        }
        if (line.trimStart().startsWith("//")) {
            continue;
        }
        const trimmed = cutTrailing(line).replace(/\s+$/, "");
        kept.push(trimmed || !line.trim() ? trimmed : "");
    }

    const tidied = [];
    for (const line of kept) {
        if (!line.trim() && tidied.length && !tidied[tidied.length - 1].trim()) {
            continue;
        }
        tidied.push(line);
    }
    while (tidied.length && !tidied[tidied.length - 1].trim()) {
        tidied.pop();
    }
    return tidied.length ? `${tidied.join("\n")}\n` : "";
}
