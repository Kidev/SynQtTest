# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0

"""Which build `synqt build` and `synqt dev` actually ask CMake for.

The profile used to reach nothing. `synqt build` defaulted to `--release`, and the flag was
read in exactly one place: the word printed in the summary line. Every build was the same
build, and one of the two words it printed was a lie. These pin the flags to the configure
command that comes out the other end.
"""

import unittest

from synqt import cli, profiles


def _args(argv):
    return cli.build_parser().parse_args(argv)


class WhatTheFlagsParseTo(unittest.TestCase):
    def test_build_defaults_to_debug(self):
        # The flip. A build nobody asked to be a release is not one.
        self.assertEqual(_args(["build"]).profile_name, "debug")

    def test_release_and_debug_are_the_two_shorthands(self):
        self.assertEqual(_args(["build", "--release"]).profile_name, "release")
        self.assertEqual(_args(["build", "--debug"]).profile_name, "debug")

    def test_custom_names_a_cmake_build_type(self):
        parsed = _args(["build", "--custom", "RelWithDebInfo"])
        self.assertEqual(parsed.custom_type, "RelWithDebInfo")

    def test_custom_refuses_a_type_cmake_does_not_have(self):
        # CMake does not warn about an unknown CMAKE_BUILD_TYPE; it silently supplies no
        # optimisation flags, so the refusal has to happen here.
        with self.assertRaises(SystemExit):
            _args(["build", "--custom", "Fast"])

    def test_the_three_are_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            _args(["build", "--release", "--debug"])
        with self.assertRaises(SystemExit):
            _args(["build", "--release", "--custom", "Debug"])

    def test_dev_takes_them_too(self):
        self.assertEqual(_args(["dev"]).profile_name, "debug")
        self.assertEqual(_args(["dev", "--release"]).profile_name, "release")

    def test_serve_takes_no_profile_because_it_reads_the_deploy_layout(self):
        # `synqt serve` launches build/<entity>/, which is where every profile installs to
        # and which therefore holds whichever was built last. A profile flag there would
        # name a directory serve never reads, which is worse than not having one.
        self.assertFalse(hasattr(_args(["serve"]), "profile_name"))
        with self.assertRaises(SystemExit):
            _args(["serve", "--release"])

    def test_strip_is_available_on_its_own(self):
        self.assertTrue(_args(["build", "--custom", "Release", "--strip"]).strip)
        self.assertFalse(_args(["build", "--custom", "Release"]).strip)


class WhatTheProfileResolvesTo(unittest.TestCase):
    """The table itself is tested in test_profiles.py; this is that the CLI reads it."""

    def test_release_resolves_per_environment(self):
        self.assertEqual(profiles.build_type("release", "wasm"), "MinSizeRel")
        self.assertEqual(profiles.build_type("release", "host"), "Release")

    def test_custom_overrides_the_shorthands_when_both_could_apply(self):
        parsed = _args(["build", "--custom", "MinSizeRel"])
        self.assertEqual(cli.resolved_profile(parsed), ("custom", "MinSizeRel"))
        self.assertEqual(cli.resolved_profile(_args(["build", "--release"])),
                         ("release", ""))
        self.assertEqual(cli.resolved_profile(_args(["build"])), ("debug", ""))


if __name__ == "__main__":
    unittest.main()
