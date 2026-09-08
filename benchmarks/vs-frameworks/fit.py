#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0

"""Split each column's cost into the part it pays per publish and the part it pays per
subscriber.

"Node is ahead on throughput" is not an actionable sentence. A column that is slow because
it does something expensive once before it has sent anything and a column that is slow
because every extra subscriber costs it are two different stacks with two different things
to fix, and one subscriber count cannot tell them apart. Two sizes can, four are better,
and this is the arithmetic the README quotes:

    cost = fixed + subscribers x marginal

fitted by least squares over the sweep in each result file.

    python3 benchmarks/vs-frameworks/fit.py benchmarks/results/vs-fw-*.json

It used to be done by hand. A number a reader cannot re-derive from the committed files is
a number that quietly goes stale, and the fit under "what the gap is made of" did exactly
that: it stayed on a Node major that no other table on the page still quoted, because
refreshing it meant redoing the arithmetic rather than rerunning a script.

Two quantities are fitted, because they answer different questions and disagree in a way
worth seeing:

  propagation p50   what the median delivery waited. This is what the README's table
                    quotes. Deliveries within one publish are spread out (a stack services
                    its sockets one after another), so the median sits partway through that
                    spread and this slope is a per-subscriber cost as the middle subscriber
                    experiences it, not the full one.
  cost per publish  subscribers / throughput, which is wall-clock time per publish with no
                    median in it. Only meaningful on a saturating run: under pacing the
                    throughput is the pacing's and the fit reads back the metronome.

Give it a saturating sweep. Under pacing, a stack that keeps up spends most of the interval
idle, the four points sit almost on a flat line, and the intercept comes out negative,
which is the fit saying it was handed the wrong data rather than an answer.

The payload mode answers the question the fit alone cannot: whether a marginal cost is a
copy or a fixed per-socket overhead.

    python3 benchmarks/vs-frameworks/fit.py --payloads sweeps/payload

A per-socket copy of the payload grows with the payload; a per-socket syscall, wakeup and
dispatch does not. Sweeping the payload and refitting at each size separates them by a
factor nothing else in this harness can, and it is why the send-side reframing that looked
like the obvious explanation of Qt's marginal cost turned out not to be it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

# The payload directory the payload mode walks: p<bytes>, one per size.
PAYLOAD_DIR = re.compile(r"^p(\d+)$")


class Fit:
    """One straight line through one column's sweep."""

    def __init__(self, fixed: float, marginal: float, quality: float, points: int) -> None:
        self.fixed = fixed
        self.marginal = marginal
        self.quality = quality
        self.points = points


def fit_line(xs: Sequence[float], ys: Sequence[float]) -> Fit | None:
    """Least squares through the sweep, with the coefficient of determination beside it.

    The quality figure is not decoration. Four points always admit a line; whether the
    stack's cost actually is one is the thing that decides how much of the split to believe,
    and a column whose points are not on a line has to say so rather than have a slope read
    off it anyway.
    """
    count = len(xs)
    if count < 2:
        return None
    meanX = sum(xs) / count
    meanY = sum(ys) / count
    spread = sum((x - meanX) ** 2 for x in xs)
    if spread <= 0.0:
        return None
    marginal = sum((x - meanX) * (y - meanY) for x, y in zip(xs, ys)) / spread
    fixed = meanY - (marginal * meanX)
    total = sum((y - meanY) ** 2 for y in ys)
    residual = sum((y - (fixed + (marginal * x))) ** 2 for x, y in zip(xs, ys))
    quality = 1.0 if total <= 0.0 else 1.0 - (residual / total)
    return Fit(fixed, marginal, quality, count)


def sweep_points(data: Dict[str, Any], quantity: str) -> Tuple[List[float], List[float]]:
    """The (subscribers, microseconds) pairs one result file offers for one quantity."""
    xs: List[float] = []
    ys: List[float] = []
    for entry in data.get("sweep", []):
        subscribers = float(entry.get("subscribers", 0))
        if subscribers <= 0.0:
            continue
        if quantity == "p50":
            value = entry.get("propagation", {}).get("p50")
            if value is None:
                continue
            microseconds = float(value) * 1000.0
        else:
            throughput = float(entry.get("throughput_msgs_per_sec", 0.0))
            if throughput <= 0.0:
                continue
            # Deliveries per second over N subscribers is publishes per second, so its
            # reciprocal is the wall-clock time one publish took the whole fleet.
            microseconds = subscribers / throughput * 1e6
        xs.append(subscribers)
        ys.append(microseconds)
    return xs, ys


def load(paths: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    """Result files keyed by the stack that wrote them, newest wins on a repeat."""
    results: Dict[str, Dict[str, Any]] = {}
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        # The process sweep writes into the same directory under the same prefix and is not
        # this shape at all, so a glob that catches it must drop it here rather than fit a
        # line through whatever its keys happen to be called.
        if data.get("benchmark") != "vs-frameworks-live":
            continue
        results[data.get("stack", Path(path).stem)] = data
    return results


def micro(value: float) -> str:
    """A microsecond figure at the precision it is worth, which is not four decimals."""
    if abs(value) >= 100.0:
        return f"{value:.0f}"
    if abs(value) >= 10.0:
        return f"{value:.1f}"
    return f"{value:.2f}"


def print_fits(results: Dict[str, Dict[str, Any]], quantity: str) -> None:
    label = "propagation p50" if quantity == "p50" else "cost per publish"
    print(f"{label}: fixed + subscribers x marginal, least squares")
    print()
    print(f"  {'column':<20} {'fixed/publish':>14} {'marginal/sub':>14} {'R2':>7}  sizes")
    saturated = True
    for stack, data in results.items():
        if not data.get("saturated", False):
            saturated = False
        xs, ys = sweep_points(data, quantity)
        fit = fit_line(xs, ys)
        if fit is None:
            print(f"  {stack:<20} {'too few sizes to fit':>37}")
            continue
        sizes = ",".join(str(int(x)) for x in xs)
        print(f"  {stack:<20} {micro(fit.fixed) + ' us':>14} "
              f"{micro(fit.marginal) + ' us':>14} {fit.quality:>7.3f}  {sizes}")
    print()
    if not saturated:
        print("  Note: at least one column was paced, not saturated. A paced run spends the")
        print("  interval idle between ticks, so its points do not lie on this line and its")
        print("  intercept is not a fixed cost. Rerun with --saturate.")
        print()


def print_payload_sweep(root: Path, quantity: str) -> int:
    """Refit at every payload size, so a copy can be told from a per-socket overhead."""
    sizes: List[Tuple[int, Dict[str, Dict[str, Any]]]] = []
    for child in sorted(root.iterdir()):
        matched = PAYLOAD_DIR.match(child.name)
        if not child.is_dir() or matched is None:
            continue
        files = sorted(str(path) for path in child.glob("vs-fw-*.json"))
        if files:
            sizes.append((int(matched.group(1)), load(files)))
    if not sizes:
        print(f"no p<bytes>/ result directories under {root}", file=sys.stderr)
        return 2
    sizes.sort(key=lambda item: item[0])

    stacks: List[str] = []
    for _, results in sizes:
        for stack in results:
            if stack not in stacks:
                stacks.append(stack)

    label = "propagation p50" if quantity == "p50" else "cost per publish"
    print(f"marginal cost per subscriber against payload size, fitted from {label}")
    print()
    header = "  " + f"{'column':<20}" + "".join(f"{str(size) + 'B':>11}" for size, _ in sizes)
    print(header)
    marginals: Dict[str, Dict[int, float]] = {}
    for stack in stacks:
        cells: List[str] = []
        for size, results in sizes:
            data = results.get(stack)
            fit = fit_line(*sweep_points(data, quantity)) if data else None
            if fit is None:
                cells.append(f"{'-':>11}")
                continue
            marginals.setdefault(stack, {})[size] = fit.marginal
            cells.append(f"{micro(fit.marginal):>11}")
        print(f"  {stack:<20}" + "".join(cells))
    print()
    print("  (microseconds per subscriber per publish)")
    print()

    print("  What the payload buys each stack, per subscriber:")
    print()
    # No line is fitted through this one. The shape is not a line: every column measured so
    # far is flat across the first few sizes and then turns up, which is exactly what a cost
    # that is an overhead at small payloads and a copy at large ones looks like. Fitting a
    # straight line through both halves would report an average slope that is wrong
    # everywhere and would hide the one number a reader wants, which is where the turn is.
    smallest = min(size for size, _ in sizes)
    largest = max(size for size, _ in sizes)
    print(f"  {'column':<20} {'at ' + str(smallest) + 'B':>11} {'at ' + str(largest) + 'B':>11} "
          f"{'growth':>8} {'knee':>9} {'per KiB above it':>18}")
    for stack in stacks:
        byPayload = marginals.get(stack, {})
        if smallest not in byPayload or largest not in byPayload:
            continue
        base = byPayload[smallest]
        top = byPayload[largest]
        # The knee: the first size whose marginal cost is a quarter above the smallest
        # payload's. Below it the bytes are not what the stack is paying for, whatever else
        # is true; above it they are part of it. A quarter rather than anything tighter
        # because run-to-run spread on this figure is a few percent, not a few tenths.
        knee = next((size for size in sorted(byPayload)
                     if byPayload[size] > base * 1.25), None)
        # Read between the two largest sizes rather than across the whole sweep, because
        # that is the half where the payload is actually being paid for.
        ordered = sorted(byPayload)
        stride = ((byPayload[ordered[-1]] - byPayload[ordered[-2]])
                  / ((ordered[-1] - ordered[-2]) / 1024.0))
        print(f"  {stack:<20} {micro(base) + ' us':>11} {micro(top) + ' us':>11} "
              f"{top / base if base > 0 else 0:>7.1f}x "
              f"{(str(knee) + 'B') if knee else 'none':>9} {micro(stride) + ' us':>18}")
    print()
    print(f"  A column with no knee pays the same per subscriber whatever the frame carries,")
    print(f"  so its marginal cost is a syscall, a wakeup and a dispatch, not the bytes. One")
    print(f"  with a knee copies the payload per subscriber above that size, and the last")
    print(f"  column says what each further KiB then costs it.")
    print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", nargs="*",
                        help="result files from one run of run-bench.sh")
    parser.add_argument("--payloads", metavar="DIR",
                        help="a directory of p<bytes>/ subdirectories, one sweep each")
    parser.add_argument("--quantity", choices=["p50", "publish"], default="p50",
                        help="what to fit: the median delivery's wait (the default, and "
                             "what the README quotes) or wall-clock time per publish")
    arguments = parser.parse_args()

    if arguments.payloads:
        return print_payload_sweep(Path(arguments.payloads), arguments.quantity)
    if not arguments.results:
        parser.error("give it result files, or --payloads with a directory of sweeps")
    print_fits(load(arguments.results), arguments.quantity)
    return 0


if __name__ == "__main__":
    sys.exit(main())
