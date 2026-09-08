# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0

"""The arithmetic behind the fixed and marginal split, held to sweeps whose answer is known.

The split under "what the gap is made of" in benchmarks/vs-frameworks/README.md used to be
done by hand, and a hand-computed number is one nobody re-derives: it stayed on a Node major
no other table on the page still quoted, because refreshing it meant redoing the arithmetic.
fit.py replaced the arithmetic, and this holds fit.py to sweeps built from a fixed cost and a
marginal cost it is then asked to recover.

The payload cases are the ones worth having twice over. The whole argument that Qt's
per-subscriber cost is an overhead rather than a copy rests on the knee, so a knee reported
where there is none, or missed where there is one, would quietly turn that argument around.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vs-frameworks"))

import fit  # noqa: E402


def sweep(fixed, marginal, sizes=(10, 50, 100, 250), stack="synthetic", saturated=True):
    """A result file whose cost is exactly `fixed + subscribers x marginal`, in milliseconds."""
    return {
        "benchmark": "vs-frameworks-live",
        "stack": stack,
        "saturated": saturated,
        "sweep": [{"subscribers": n,
                   "propagation": {"p50": (fixed + (n * marginal)) / 1000.0},
                   "throughput_msgs_per_sec": n / ((fixed + (n * marginal)) / 1e6)}
                  for n in sizes],
    }


def test_a_line_is_recovered_from_the_sweep_it_was_built_from():
    result = fit.fit_line(*fit.sweep_points(sweep(23.0, 12.8), "p50"))
    assert result is not None
    assert abs(result.fixed - 23.0) < 0.01
    assert abs(result.marginal - 12.8) < 0.01
    assert result.quality > 0.999


def test_the_two_quantities_agree_on_a_sweep_where_they_should():
    # Cost per publish is derived from throughput and the p50 is the stamped interval, so on
    # a synthetic sweep built from one line the two have to read back the same line. They
    # disagree on real data, and this is what says the disagreement is the data's.
    made = sweep(40.0, 9.0)
    byLatency = fit.fit_line(*fit.sweep_points(made, "p50"))
    byThroughput = fit.fit_line(*fit.sweep_points(made, "publish"))
    assert abs(byLatency.marginal - byThroughput.marginal) < 0.01
    assert abs(byLatency.fixed - byThroughput.fixed) < 0.01


def test_a_sweep_of_one_size_is_refused_rather_than_fitted():
    # One point cannot tell a fixed cost from a marginal one. This page learned that the
    # expensive way, reading a single N=40 sample as an 8% lead that was true at 40 and false
    # at 250, so the refusal is the lesson made mechanical.
    assert fit.fit_line(*fit.sweep_points(sweep(23.0, 12.8, sizes=(40,)), "p50")) is None


def test_a_paced_run_is_reported_as_one(capsys):
    fit.print_fits({"paced": sweep(23.0, 12.8, saturated=False)}, "p50")
    assert "paced, not saturated" in capsys.readouterr().out


def test_a_saturating_run_carries_no_warning(capsys):
    fit.print_fits({"saturating": sweep(23.0, 12.8)}, "p50")
    assert "paced, not saturated" not in capsys.readouterr().out


def _payload_tree(root, marginal_by_payload, stack):
    for payload, marginal in marginal_by_payload.items():
        directory = root / f"p{payload}"
        directory.mkdir()
        import json
        (directory / f"vs-fw-{stack}.json").write_text(
            json.dumps(sweep(20.0, marginal, stack=stack)), encoding="utf-8")


def test_a_cost_that_does_not_move_with_the_payload_has_no_knee(tmp_path, capsys):
    # The `qt-raw` shape: 64 bytes and 4 KiB cost the same per subscriber, which is what
    # says the cost is a syscall and a dispatch rather than the bytes.
    _payload_tree(tmp_path, {64: 9.4, 256: 9.2, 1024: 9.5, 4096: 9.9}, "flat")
    assert fit.print_payload_sweep(tmp_path, "p50") == 0
    printed = capsys.readouterr().out
    assert "none" in printed


def test_a_cost_that_grows_with_the_payload_reports_its_knee(tmp_path, capsys):
    # The QtRemoteObjects shape: flat, then turning hard once the payload is big enough for
    # a per-subscriber copy to dominate.
    _payload_tree(tmp_path, {64: 10.6, 256: 10.7, 1024: 11.7, 4096: 12.7, 16384: 39.9}, "copies")
    assert fit.print_payload_sweep(tmp_path, "p50") == 0
    printed = capsys.readouterr().out
    assert "16384B" in printed
    assert "none" not in printed


def test_a_directory_with_no_sweeps_says_so_rather_than_printing_nothing(tmp_path):
    assert fit.print_payload_sweep(tmp_path, "p50") == 2
