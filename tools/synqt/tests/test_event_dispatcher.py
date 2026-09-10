# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0

"""Which event dispatcher a generated entity asks for, and where the ask has to sit.

On Linux Qt takes GLib's dispatcher whenever GLib is installed, and GLib keeps every
watched descriptor in one poll list that a socket walks whenever it toggles its write
notifier. A fan-out toggles one per connection per publish, so the event loop's own cost
grows with the square of the subscriber count: measured on benchmarks/vs-frameworks, the
polling dispatcher delivers 18% more at ten subscribers and 52% more at two hundred and
fifty, and it is the widening that identifies the cause.

Two things about it are easy to get wrong and are what these tests hold. The ask must come
before the QCoreApplication, because that is when the dispatcher is chosen and afterwards
the call is inert -- and nothing reports that it was too late. And it belongs to the
entities that fan out, not to a desktop client, whose one socket gains nothing and whose
native GTK dialogs are exactly what GLib's dispatcher is there for.
"""

import unittest

from synqt import maingen


ASK = "SynQt::preferPollingEventDispatcher();"


def base_config():
    return {
        "project": {"name": "app"},
        "entities": [
            {"name": "client", "type": "client", "path": "client"},
            {"name": "web", "type": "web_edge", "path": "web"},
            {"name": "store", "type": "service", "path": "store"},
        ],
        "connect_points": [
            {"owner": "web", "consumers": ["client"]},
            {"owner": "store", "consumers": ["web"]},
        ],
    }


def entity(config, name):
    return next(item for item in config["entities"] if item["name"] == name)


class EventDispatcherChoiceTest(unittest.TestCase):
    def _servers(self):
        config = base_config()
        return {
            "edge": maingen.render_edge_main(config, entity(config, "web")),
            "service": maingen.render_service_main(config, entity(config, "store")),
        }

    def test_every_fanning_out_entity_asks_for_it(self):
        for kind, source in self._servers().items():
            with self.subTest(kind=kind):
                self.assertIn(ASK, source)

    def test_the_ask_comes_before_the_application(self):
        # After the application is constructed the dispatcher already exists, the call does
        # nothing, and nothing says so: the entity would simply run at GLib's speed with a
        # line in it claiming otherwise.
        for kind, source in self._servers().items():
            with self.subTest(kind=kind):
                self.assertLess(source.index(ASK), source.index("Application app{"),
                                f"the {kind} asks for the dispatcher too late")

    def test_the_header_that_declares_it_is_included(self):
        for kind, source in self._servers().items():
            with self.subTest(kind=kind):
                self.assertIn('#include "pollingdispatcher.h"', source)

    def test_a_desktop_client_is_left_on_the_platform_default(self):
        # One socket, so nothing to win, and GLib's dispatcher is what a GTK platform theme
        # needs for its native dialogs. A client that quietly lost those would be paying a
        # visible cost for an invisible non-gain.
        config = base_config()
        source = maingen.render_client_main(config, uri="App",
                                            entity=entity(config, "client"))
        self.assertNotIn(ASK, source)


class MonitorDispatcherTest(unittest.TestCase):
    """A monitor serves a browser console, so it fans out like an edge does."""

    def test_a_monitor_asks_for_it_too(self):
        config = base_config()
        config["monitoring"] = {"entity": "watch"}
        config["entities"].append({"name": "watch", "type": "monitor",
                                   "public": {"host": "127.0.0.1", "port": 8443}})
        source = maingen.render_monitor_main(config, entity(config, "watch"))
        self.assertIn(ASK, source)
        self.assertLess(source.index(ASK), source.index("Application app{"))


if __name__ == "__main__":
    unittest.main()
