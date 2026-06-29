<!-- SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# CodeMirror, vendored

The `.js` files beside this one are [CodeMirror 6](https://codemirror.net/) and the packages
it is built from, under the MIT licence in `LICENSE`. They are somebody else's source and are
never edited here: to change one, fetch it again.

The editor's file pane is a real code editor rather than a textarea with a coloured copy
behind it, and this is what makes it one. Only the colouring is ours: the syntax the pane
paints is [`source.js`](../source.js), turned into CodeMirror decorations by
[`editor.js`](../editor.js), so there is one description of what QML, YAML, SQL and a
contract look like rather than one per editor.

## What is here, and why each one

| file | package | why |
| --- | --- | --- |
| `codemirror-state.js` | `@codemirror/state` | the document, selections and transactions |
| `codemirror-view.js` | `@codemirror/view` | the editor itself, and the decorations the colouring is |
| `codemirror-commands.js` | `@codemirror/commands` | undo, and the key bindings anyone expects |
| `codemirror-language.js` | `@codemirror/language` | bracket matching |
| `lezer-common.js`, `lezer-highlight.js` | `@lezer/*` | what `@codemirror/language` is built on |
| `style-mod.js`, `w3c-keyname.js`, `crelt.js`, `marijn-find-cluster-break.js` | | what the four above are built on |

## How they were made

There is no build step in this repository and there is not going to be one, so these are the
published ES modules with their bare import specifiers rewritten to the file names here. That
is the whole of the change: one file per package, so every package shares one copy of its
dependencies, which matters because CodeMirror's facets are identified by object identity and
two copies of `@codemirror/state` do not agree about anything.

They were fetched from [esm.sh](https://esm.sh), which serves each package as one module and
imports its dependencies by absolute path. Following those paths and rewriting each one to
`./<package>.js` is the whole of it, plus dropping the trailing `sourceMappingURL` comment,
which named a `.map` file that is not vendored and would be a 404 the first time anybody
opened developer tools. The versions are in the comment at the top of each file.

## The rules these files live under

- **Never edited.** Nothing here carries an SPDX header of ours, because none of it is ours.
- **Nothing off-origin.** The published copy of the editor at `/designer/` has no server over
  it to refuse a fetch, so the docs hook (`tools/docs-hooks/designer.py`) reads every file
  here and refuses to publish one that names another host. These name none.
- **No `eval`.** The page is served under `default-src 'none'` with no `unsafe-eval`, and
  CodeMirror needs none.
- **Inside a shadow root.** CodeMirror builds its own stylesheet at run time. Against a
  document, style-mod builds it as a `<style>` element with text in it, which the same policy
  refuses; against a shadow root it builds it as a constructed `CSSStyleSheet`, which no
  policy has an opinion about. That is why [`editor.js`](../editor.js) attaches one, and why
  the editor's CSS is a stylesheet of its own for that root to link. It needs
  `adoptedStyleSheets` on a `ShadowRoot`, which every browser the editor is used in has had
  for years.
