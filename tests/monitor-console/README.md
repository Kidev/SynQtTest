# monitor-console

The monitoring console, end to end, in a real browser.

Everything this suite asserts is invisible to a compiler:

- a bundle outside the caller's scope answers **404**, not 403, so it is not addressable;
- the sign-in gate is a page with a form, and its inline script has to survive the edge's
  strict Content-Security-Policy;
- signing in raises the same session, so the **same URL** returns a different bundle;
- the console is a Qt Quick scene that either draws or does not;
- and it reached the monitor, which the monitor's own record is what proves.

The project is written by the scaffolder when the suite runs
([`make-project.py`](make-project.py)), not checked in, so what loads is what
`synqt add entity <name> --type monitor` produces today rather than what it produced when
somebody pasted it into the repository.

## Running it

```console
$ bash tests/monitor-console/run-monitor-console.sh
```

Phases 1 and 2 (scaffold, build the monitor and the reporting edge) need only the host kit.
Phases 3 and 4 need the WebAssembly kit at `$QT_WASM` and a browser runtime; without the
kit the suite says so and stops rather than failing on a toolchain the host was never
given.

## What it found

Written after the monitoring feature was complete and every other suite was green. It found
seven defects, four of them outside monitoring:

| What | Where |
| --- | --- |
| The monitor's bundle gate was wired to entity names, so the console could never be delivered | `maingen.render_monitor_main`, `run.dev_command` |
| The reporting path called into a Replica across threads (`Timers cannot be stopped from another thread`) | `IngestClient::send` |
| `Server` did not resolve for a console client, though the monitor is that client's edge | `maingen.render_client_main` |
| The scaffolded console's attached handler named the owner instead of the contract, so the QML would not load at all | `monitorscaffold.console_qml` |
| Every console session stayed connected to the process-wide service after its Source was gone | `monitorentity.CONSOLE_SOURCE_QML` |
| A scaffolded monitor took the port the edge already had | `monitorscaffold.free_port`, plus a `synqt check` rule |
| An edge aborted an idle keep-alive HTTP connection and recorded it as a refused upgrade | `WebEdge::trackPendingUpgrade`; see below |

## The last one, and what it took to close it

`WebEdge` armed the handshake deadline on every accepted socket and cancelled it only when
a WebSocket upgrade arrived. An ordinary HTTP connection therefore had
`security.handshake_timeout_ms` to live whatever it was doing: past that the socket was
aborted and `upgradeRejected("handshake timeout")` emitted. A browser keeping a connection
alive between fetches, or a single response slower than the deadline, was cut off by the
server it was talking to, and the operations record gained a refusal nobody made. An early
run of this suite recorded four of them per session from a browser that was only loading
the console.

The deadline now ends at the first byte the peer sends, which leaves it bounding the thing
it was for: a socket that connects and stays silent.
`tests/m5-webedge`'s `aKeepAliveConnectionThatFetchedThePageIsNotClosedUnderIt` is the
regression guard, and it fails without the fix.

Getting there meant fixing the instrument first. Every attempted fix appeared to push
[`tests/memory`](../memory)'s `theEdgeLetsGoOfABrowserThatComesAndGoes` from inside its
64-bytes-per-cycle budget to 660-1020 bytes per connection, which no version of a single
signal connection explains. It was not the fix. That suite compared the heap after N cycles
against the heap before them and required the difference to be near zero, and the heap
under that workload is not a straight line: it drops about 228 KB in one move partway
through a long run and ends 200 KB below where it started. The old check failed a build
that retained nothing per connection and would have passed one that retained an object per
connection. It measures the slope between two equal windows now, and
`theBudgetCanTellALeakFromABusyProcess` leaks a known amount on purpose to prove the budget
can still come back negative.
