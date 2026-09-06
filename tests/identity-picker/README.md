# tests/identity-picker

The development scope picker, in a real browser, with a real cookie jar.

```bash
bash tests/identity-picker/run-identity-picker.sh
```

## What only a browser can say

`tests/m5-webedge` already drives the picker's routes: it proves the page lists the
project's declared scopes and nothing else, that a posted index is bounds-checked, that a
per-tab choice answers `303` with `Location: /?s=<nonce>` and a `synqt_session_<nonce>`
cookie, and that the routes do not exist at all in an edge nobody asked for the picker.

What it cannot say is what a browser does with two of those cookies. Two tabs of one
browser context share one jar, because RFC 6265 scopes a cookie to a host and not a port,
and "the second sign-in did not become the first" is a statement about that jar. That is
this suite: three tabs of one context, a moderator in one and a user in another, and the
first still a moderator afterwards.

Reverting the cookie-name resolution (`WebEdge::cookieNameFor`) to the fixed name is how
you see it fail, and the failure is the one the mechanism exists to prevent:

```
FAIL chromium: tab one became user when tab two signed in
```

## How a tab is asked who it is

The session cookie is httpOnly, so a page cannot read it. The edge answers `/` with the
bundle mapped to the caller's scope, so the project written by `make-project.py` maps each
of its three scopes to a directory holding one line of HTML. Which line came back is the
answer.

No WebAssembly kit is needed and no client is built: three static directories answer that
question exactly as a compiled client would, and the client this project declares exists
only so the topology is the ordinary one.

## What else it covers

- The named identities from `.dev-identities` are offered beside the scopes, and an entry
  naming a scope the project does not declare is reported on the page rather than taking
  the picker down.
- The ordinary shared sign-in still works and leaves the per-tab sessions alone, which is
  the half a per-tab mechanism is most likely to break.
