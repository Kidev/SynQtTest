<!-- SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Quick start

Install the CLI, copy one of the systems SynQt ships, and run it. Two commands after the
install and a real SynQt system is up: a client compiled to WebAssembly in your browser, a
web edge serving it, and a database the browser cannot reach. The first build downloads a
toolchain and takes a few minutes; nothing else here is slow.

Nothing on this page asks you to write any code. It is here to get something running so you
can look at it. [Getting started](getting-started.md) builds a project of your own.

## Install the CLI

```cli
curl -fsSL https://get.synqt.org/install.sh | sh
```

On Windows, in PowerShell, it is `irm https://get.synqt.org/install.ps1 | iex`. If you
already have Python, `pipx install synqt` gets you the same CLI from PyPI.

```cli
synqt version
```

That single binary is everything you install by hand. The first build downloads the rest of
the toolchain, the Qt SDK and the Emscripten compiler that turns your QML into WebAssembly,
and pins both inside the project, so every machine and every teammate compiles against the
same versions.

## Copy an example

```cli
synqt examples
```

```text
  arena  the multiplayer tutorial, materialized
  chat   a room everybody in it sees at once
  gavel  the auction tutorial, materialized
  stall  a storefront with edge-delivered campaigns

Start one with: synqt new <directory> --example <name>
```

Take the storefront. It is the one that needs nothing from you before it runs: the others
sign people in, and an OAuth app is a detour on a page called quick start.

```cli
synqt new shop --example stall
cd shop
```

That is a whole project, not a template: the same `synqt.yaml`, the same entity folders and
the same QML you would have written by hand, with `project.name` set to the directory you
named. Read `README.md` in it for what the example is doing.

## Run it

```cli
synqt dev
```

`synqt dev` is the whole development loop in one command. It issues a throwaway development
certificate authority and a certificate per entity, so the mesh links between the services
run over mutual TLS from the first second rather than from the day you remember to turn it
on. It runs `synqt check` over `synqt.yaml` first and refuses to start on a topology that
does not pass. It builds every entity, the client to WebAssembly and the rest as native
binaries. Then it starts them, owners before consumers and the edge last, and opens
[http://127.0.0.1:8080](http://127.0.0.1:8080).

The first run takes a few minutes because of the toolchain download. Every run after that is
seconds.

## What you are looking at

The storefront in the browser is a Qt Quick application compiled to WebAssembly, holding a
live [QtRemoteObjects](https://doc.qt.io/qt-6/qtremoteobjects-index.html) link to the edge
over a WebSocket. Three entities are running:

| Entity | What it is | Who can reach it |
| --- | --- | --- |
| `app` | the client, in your browser | you |
| `edge` | the web edge: serves the bundle, owns the live catalog, delivers the campaign pages | the browser, over wss |
| `stock` | the database holding the durable stock | the edge, over mutual TLS |

The browser talks to the edge and to nothing else. It holds no certificate and no route into
the mesh, so the database is not something it failed to reach: it is something it cannot
address. That is the shape of every SynQt system, and it is the [entity
model](entities.md), not a deployment choice.

Leave `synqt dev` running. It watches every `.qml` file and `synqt.yaml`, rebuilds what a
save actually affects, and reloads the browser for you. Open `client/app/Home.qml`, change a
label, save it, and watch the page come back with it.

## Or draw it first

If you would rather see the shape of a system before running one, open the
[designer](/designer/). Draw the entities and the links between them, press Export and take
it as a project, and unzip the result over a project made with `synqt new`. Nothing is
installed and nothing leaves the page. The [guide to the designer](visual-editor.md) covers
what it can do, and **Examples** in its bar opens each of the systems above on the canvas.

## Where to go next

- [Getting started](getting-started.md) builds a project of your own from an empty scaffold,
  and covers `synqt create`, which asks the security relevant questions instead of taking
  defaults.
- [The simple chat](tutorial-chat.md) is the shortest tutorial that ends in a real
  application: one room, sign-in, and a column the browser never receives.
- [The auction tutorial](tutorial.md) builds a system end to end: live bidding, then
  sign-in, then a database the browser cannot reach. `gavel` above is where it finishes.
- [Architecture](architecture.md) is the reference, from the entity model to the security
  design.
