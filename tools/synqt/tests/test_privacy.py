# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0

"""The `privacy:` block: what a project inherits by saying nothing, and what it is refused.

Two of these are about defaults rather than about validation, and they are the ones worth
reading twice. Retention has a default because Article 5(1)(e) applies whether or not anyone
configured anything, and a project that never thought about it should not be storing forever
by accident. The cookie banner does *not* have a default, for the opposite reason: the
session credential is exempt under Article 5(3) of the ePrivacy Directive, so a project with
no other cookie has nothing to ask about and a banner it never needed teaches its visitors
to dismiss the one that matters.
"""

import unittest

from synqt import appmodel, check, maingen


def project(privacy=None, identity=True):
    config = {
        "project": {"name": "app"},
        "entities": [
            {"name": "client", "type": "client", "path": "client"},
            {"name": "web", "type": "web_edge", "path": "web"},
        ],
        "connect_points": [{"owner": "web", "consumers": ["client"]}],
    }
    if identity:
        config["identity"] = {
            "providers": {"github": {"client_id": "x", "client_secret": "env:S"}},
        }
    if privacy is not None:
        config["privacy"] = privacy
    return config


def errors(config):
    return [message for message in check.validate(config)[1]
            if message.startswith("error:")]


class RetentionDefaultTest(unittest.TestCase):
    def test_a_project_that_says_nothing_inherits_a_period(self):
        self.assertEqual(appmodel.retention_days(project()),
                         appmodel.DEFAULT_RETENTION_DAYS)

    def test_a_shorter_period_is_kept_as_written(self):
        # The whole point of the default is to fill a gap. A project that has decided to keep
        # data for thirty days has decided something stricter than the default, and raising
        # it to the default would be the framework overriding a data protection decision in
        # the direction that keeps more.
        self.assertEqual(appmodel.retention_days(project({"retention_days": 30})), 30)

    def test_a_longer_period_is_also_kept_as_written(self):
        # The default is not a ceiling anyone here is in a position to enforce: what is
        # lawful depends on what the project stores and why, and a records statute can
        # require years. Naming a period is the project taking that decision.
        self.assertEqual(appmodel.retention_days(project({"retention_days": 3650})), 3650)

    def test_the_period_reaches_the_client(self):
        config = project({"retention_days": 90})
        source = maingen.render_client_main(config, uri="App",
                                            entity=config["entities"][0])
        self.assertIn("config.retentionDays = 90;", source)


class CookieBannerDefaultTest(unittest.TestCase):
    def test_no_categories_until_a_project_declares_one(self):
        self.assertEqual(appmodel.cookie_categories(project()), [])
        self.assertEqual(appmodel.cookie_categories(project({"policy": "/privacy"})), [])

    def test_a_declared_category_reaches_the_client(self):
        config = project({"cookies": ["analytics", "ads"]})
        self.assertEqual(appmodel.cookie_categories(config), ["analytics", "ads"])
        source = maingen.render_client_main(config, uri="App",
                                            entity=config["entities"][0])
        self.assertIn('config.cookieCategories = {QStringLiteral("analytics"), '
                      'QStringLiteral("ads")};', source)

    def test_a_project_with_no_categories_emits_none(self):
        source = maingen.render_client_main(project(), uri="App",
                                            entity=project()["entities"][0])
        self.assertNotIn("cookieCategories", source)


class ErasureTest(unittest.TestCase):
    def test_it_is_off_unless_asked_for(self):
        self.assertFalse(appmodel.erasure_offered(project()))
        self.assertFalse(appmodel.erasure_offered(project({"policy": "/privacy"})))

    def test_offering_it_reaches_the_client(self):
        config = project({"erasure": True})
        self.assertTrue(appmodel.erasure_offered(config))
        source = maingen.render_client_main(config, uri="App",
                                            entity=config["entities"][0])
        self.assertIn("config.erasureOffered = true;", source)

    def test_offering_it_without_identity_is_refused(self):
        # The component is visible only to a signed-in visitor, so a project with no login
        # ships a button nobody can ever see, against a promise its privacy policy is
        # presumably making.
        found = errors(project({"erasure": True}, identity=False))
        self.assertTrue([m for m in found if "privacy.erasure" in m], found)

    def test_offering_it_with_identity_is_fine(self):
        found = errors(project({"erasure": True}))
        self.assertEqual([m for m in found if "privacy.erasure" in m], [])


class MissingBlockTest(unittest.TestCase):
    def test_a_client_project_with_no_block_is_told_where_it_is(self):
        # A note, never a refusal: whether an app owes anybody a privacy policy depends on
        # where its visitors are and what it collects, and a config file cannot answer that.
        messages = check.validate(project())[1]
        notes = [m for m in messages if m.startswith("warn:") and "privacy:" in m]
        self.assertEqual(len(notes), 1, messages)
        self.assertIn("730", notes[0])

    def test_declaring_the_block_silences_it(self):
        messages = check.validate(project({"policy": "/privacy"}))[1]
        self.assertEqual([m for m in messages if m.startswith("warn:") and "privacy:" in m],
                         [])

    def test_a_project_with_no_client_is_not_told(self):
        # A mesh of services serves no browser, so there is no page for a footer to sit on.
        config = {
            "project": {"name": "app"},
            "entities": [
                {"name": "store", "type": "service", "path": "store"},
                {"name": "jobs", "type": "service", "path": "jobs"},
            ],
            "connect_points": [{"owner": "store", "consumers": ["jobs"]}],
        }
        messages = check.validate(config)[1]
        self.assertEqual([m for m in messages if "privacy:" in m], [])


class ShapeTest(unittest.TestCase):
    def test_a_non_map_block_is_refused(self):
        found = errors(project(["policy"]))
        self.assertTrue([m for m in found if "privacy must be a map" in m], found)

    def test_a_non_text_url_is_refused(self):
        found = errors(project({"policy": 42}))
        self.assertTrue([m for m in found if "privacy.policy" in m], found)

    def test_a_retention_that_is_not_a_period_is_refused(self):
        for value in (0, -30, "a year", True):
            with self.subTest(value=value):
                found = errors(project({"retention_days": value}))
                self.assertTrue([m for m in found if "privacy.retention_days" in m], found)

    def test_a_category_that_is_not_a_name_is_refused(self):
        found = errors(project({"cookies": ["analytics", 7]}))
        self.assertTrue([m for m in found if "privacy.cookies" in m], found)

    def test_a_well_formed_block_passes(self):
        found = errors(project({
            "policy": "/privacy",
            "legal_notice": "/legal",
            "contact": "privacy@example.com",
            "retention_days": 365,
            "cookies": ["analytics"],
            "erasure": True,
        }))
        self.assertEqual([m for m in found if "privacy" in m], [])


if __name__ == "__main__":
    unittest.main()
