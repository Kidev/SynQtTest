#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0

# Make ccache able to share entries between the many builds one test run performs. Sourced by
# tests/run-all.sh and tests/run-coverage.sh, which is every entry point CI uses; the exports
# reach the per-suite runners because those are child processes.
#
# cmake/SynQtBuildFlags.cmake is what routes the compiler through ccache (or sccache on MSVC),
# and it does that for every build of SynQt including a user's application. This file is the
# part that is only right for SynQt's own test tree, which is why it is here and not there.
#
# The problem it solves, measured rather than assumed. One run of tests/run-all.sh compiles
# the framework about ten times: every generated application add_subdirectory()s it from
# ${SYNQT_ROOT}, so the whole-tree suite builds it once, tests/appgen-native six more times for
# its six topologies, and custom-provider, desktop-client and monitor-console once each. With
# ccache installed and nothing else done, tests/appgen-native reported 0 hits out of 676
# compiles. Two builds of one target from one source tree, differing only in which directory
# they were configured into, shared nothing at all.
#
# The cause is ccache's `hash_dir`, which is on by default and puts the current working
# directory into the hash whenever the compiler is emitting debug information. That is the
# correct default, because the directory really is recorded in the debug info; it is also
# exactly what every build here does, since they are all RelWithDebInfo. Turning it off took
# the same suite from 0 hits to 330 of 676 on a completely cold cache, and 191 seconds to 153.
#
# What it costs: an object served from the cache carries the compilation directory of the build
# that first produced it, so DW_AT_comp_dir can name a sibling build tree. Line tables and
# absolute source paths are unaffected, which is nearly all of what a debugger needs here; a
# generated file referenced relatively (a moc translation unit, say) is the case where a
# debugger would look in the wrong directory for the source. That is a fair trade for a test
# run and not one to impose on someone's application, which is the whole reason this is scoped
# to the two scripts that source it. Unset CCACHE_NOHASHDIR to get the strict behaviour back.
#
# Nothing here needs ccache to exist: these are variables ccache reads, and if it is not
# installed the CMake side never invokes it and they are inert.
export CCACHE_NOHASHDIR=1
