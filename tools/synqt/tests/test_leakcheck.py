# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0

"""The leak gate's own reading: who a lost allocation belongs to.

`tests/memory/leakcheck.py` fails a build when LeakSanitizer loses something this
repository allocated. What it must not do is fail one for something a library allocated
while reacting to us, because that is a gate people learn to skip.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


def _leakcheck():
    """The gate's module, loaded from where it lives rather than installed."""
    path = REPO / "tests" / "memory" / "leakcheck.py"
    spec = importlib.util.spec_from_file_location("leakcheck", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _report(tmp_path: Path, body: str) -> Path:
    logs = tmp_path / "leaks"
    logs.mkdir()
    (logs / "asan.1").write_text(body, encoding="utf-8")
    return logs


# The real one, trimmed: QtRO builds a dynamic Replica's metaobject inside its own
# onClientRead and keeps it. The only frame of ours is the `emit readyRead()` that drove
# the socket read, five frames below the allocation and under a signal dispatch.
UPSTREAM_UNDER_A_DISPATCH = """
=================================================================
==1==ERROR: LeakSanitizer: detected memory leaks

Direct leak of 1856 byte(s) in 4 object(s) allocated from:
    #0 0x1 in calloc (/usr/lib/libasan.so.8+0x1)
    #1 0x2 in QMetaObjectBuilder::toMetaObject() const qtbase/src/corelib/kernel/qmetaobjectbuilder.cpp:1494
    #2 0x3 in registerDefinition qtremoteobjects/src/remoteobjects/qremoteobjectnode.cpp:1126
    #3 0x4 in QRemoteObjectMetaObjectManager::addDynamicType qtremoteobjects/src/remoteobjects/qremoteobjectnode.cpp:1282
    #4 0x5 in QRemoteObjectNodePrivate::onClientRead(QObject*) qtremoteobjects/src/remoteobjects/qremoteobjectnode.cpp:1633
    #5 0x6 in QtPrivate::QSlotObjectBase::call(QObject*, void**) qtbase/src/corelib/kernel/qobjectdefs_impl.h:462
    #6 0x7 in void doActivate<false>(QObject*, int, void**) qtbase/src/corelib/kernel/qobject.cpp:4372
    #7 0x8 in operator() {repo}/src/transport/websockettransport.cpp:42
    #8 0x9 in main {repo}/tests/m7-caller/tst_m7.cpp:516

SUMMARY: AddressSanitizer: 1856 byte(s) leaked in 4 allocation(s).
"""

# Ours, and the shape the gate exists for: the allocation itself is in src/, at the top.
OURS_AT_THE_TOP = """
=================================================================
==1==ERROR: LeakSanitizer: detected memory leaks

Direct leak of 128 byte(s) in 1 object(s) allocated from:
    #0 0x1 in operator new(unsigned long) (/usr/lib/libasan.so.8+0x1)
    #1 0x2 in SynQt::WebEdge::start() {repo}/src/edge/webedge.cpp:700
    #2 0x3 in main {repo}/tests/m5-webedge/tst_m5.cpp:120

SUMMARY: AddressSanitizer: 128 byte(s) leaked in 1 allocation(s).
"""


# A leaked graph whose members all point at each other. LeakSanitizer walks out from every
# unreachable block and tags whatever it reaches as indirect, so when the graph has no entry
# nobody points into, every block is somebody's child and nothing is reported as direct. A
# QObject tree is this shape by construction: the parent holds its children, and every child
# holds a pointer back to its parent.
ALL_INDIRECT_NO_ROOT = """
=================================================================
==1==ERROR: LeakSanitizer: detected memory leaks

Indirect leak of 4096 byte(s) in 8 object(s) allocated from:
    #0 0x1 in operator new(unsigned long) (/usr/lib/libasan.so.8+0x1)
    #1 0x2 in SynQt::WebEdge::start() {repo}/src/edge/webedge.cpp:979
    #2 0x3 in main {repo}/tests/m5-webedge/tst_m5.cpp:120

SUMMARY: AddressSanitizer: 4096 byte(s) leaked in 8 allocation(s).
"""


def test_a_process_that_leaked_whole_is_named_not_counted_as_zero(tmp_path, capsys):
    """A cycle has no direct record, and the gate used to read that as nothing lost.

    LeakSanitizer calls a block direct only when no other leaked block points at it. Give
    it a graph whose members all point at each other and every block is somebody's child,
    so it reports no direct record at all; a two-node cycle in ten lines of C reproduces
    it. Reading only direct records, a process in that shape arrived with nothing to
    contribute and passed through as clean whatever it had lost. Five of this tree's
    suites really were in that shape, m5 among them, losing 2.6 MB across 32868
    allocations while the report printed "0 records, 0 bytes" and said nothing else.

    It stays uncharged, because in a graph lost whole the allocation site is not the
    culprit. It does not stay invisible.
    """
    leakcheck = _leakcheck()
    logs = _report(tmp_path, ALL_INDIRECT_NO_ROOT.replace("{repo}", str(REPO)))
    assert leakcheck.sanitize(logs, REPO) == 0
    printed = capsys.readouterr().out
    assert "named no root" in printed
    assert "4096 bytes" in printed
    # Named by the suite, not by the pid the log file is named after.
    assert "tests/m5-webedge/tst_m5.cpp" in printed
    # Named, but not charged: the site is where the block was born, not what dropped it.
    assert "framework (src/), which is what this gate is for: 0 records" in printed


def test_a_child_of_a_named_root_is_not_mistaken_for_a_rootless_process(tmp_path, capsys):
    """The other half: where a root does exist, the split LeakSanitizer drew is worth keeping.

    An indirect record under a real direct root names a child, not a culprit. It must not
    trip the rootless report either, or every ordinary process would be listed there.
    """
    leakcheck = _leakcheck()
    body = (UPSTREAM_UNDER_A_DISPATCH.replace("{repo}", str(REPO)).rstrip()
            + ALL_INDIRECT_NO_ROOT.replace("{repo}", str(REPO)))
    logs = _report(tmp_path, body)
    assert leakcheck.sanitize(logs, REPO) == 0
    printed = capsys.readouterr().out
    assert "named no root" not in printed
    assert "held by a leaked root, allocated by us (evidence, not a verdict): 1 records" in printed


def test_a_library_reacting_to_us_is_not_charged_to_us(tmp_path, capsys):
    """Emitting a signal is not allocating.

    Above a signal dispatch the code running is a slot somebody else wrote; below it is
    whoever emitted. Without that boundary the gate charged QtRO's dynamic-metaobject
    retention to `websockettransport.cpp`, because the `emit` was nine frames down and the
    old rule looked twelve deep.
    """
    leakcheck = _leakcheck()
    logs = _report(tmp_path, UPSTREAM_UNDER_A_DISPATCH.replace("{repo}", str(REPO)))
    assert leakcheck.sanitize(logs, REPO) == 0
    printed = capsys.readouterr().out
    assert "framework (src/), which is what this gate is for: 0 records" in printed
    assert "1 roots" in printed  # counted as upstream, which is what it is


def test_an_allocation_of_ours_still_fails_the_gate(tmp_path, capsys):
    """The other half: the boundary must not have made the gate blind."""
    leakcheck = _leakcheck()
    logs = _report(tmp_path, OURS_AT_THE_TOP.replace("{repo}", str(REPO)))
    assert leakcheck.sanitize(logs, REPO) == 1
    assert "src/edge/webedge.cpp:700" in capsys.readouterr().out


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
