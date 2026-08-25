# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0

"""The `bundles:` block: which scope is served which bundle, and where it is built."""

import re

from synqt import appmodel, check


def _config(bundles=None, clients=("app",)):
    edge = {"name": "web", "type": "web_edge"}
    if bundles is not None:
        edge["bundles"] = bundles
    entities = [edge] + [{"name": name, "type": "client"} for name in clients]
    return {"entities": entities, "scopes": {"order": ["anonymous", "user"]}}, edge


def test_no_block_serves_the_one_client_to_the_default_scope():
    config, edge = _config()
    assert appmodel.bundles_for(config, edge) == {
        "anonymous": (appmodel.BUNDLE_CLIENT, "app")}


def test_a_bare_name_is_a_client_entity():
    config, edge = _config({"user": "app"})
    assert appmodel.bundles_for(config, edge) == {"user": (appmodel.BUNDLE_CLIENT, "app")}


def test_a_value_with_a_slash_is_a_static_directory():
    config, edge = _config({"anonymous": "landing/"})
    assert appmodel.bundles_for(config, edge) == {
        "anonymous": (appmodel.BUNDLE_STATIC, "landing/")}


def test_both_kinds_together():
    config, edge = _config({"anonymous": "landing/", "user": "app"})
    assert appmodel.bundles_for(config, edge) == {
        "anonymous": (appmodel.BUNDLE_STATIC, "landing/"),
        "user": (appmodel.BUNDLE_CLIENT, "app")}


def test_a_single_client_project_keeps_the_historic_output_path():
    config, _ = _config()
    client = config["entities"][1]
    assert appmodel.bundle_output_dir(config, client) == "build/client"


def test_a_multi_client_project_gets_a_directory_per_client():
    config, _ = _config(clients=("app", "gate"))
    app = config["entities"][1]
    gate = config["entities"][2]
    assert appmodel.bundle_output_dir(config, app) == "build/client-app"
    assert appmodel.bundle_output_dir(config, gate) == "build/client-gate"


def test_one_client_keeps_the_project_qml_uri():
    config, _ = _config()
    config["project"] = {"name": "shop"}
    assert appmodel.qml_uri_for(config, config["entities"][1]) == "Shop"


def test_two_clients_get_distinct_qml_uris():
    config, _ = _config(clients=("app", "gate"))
    config["project"] = {"name": "shop"}
    app = appmodel.qml_uri_for(config, config["entities"][1])
    gate = appmodel.qml_uri_for(config, config["entities"][2])
    # Distinct, or both modules would claim qrc:/qt/qml/Shop/Main.qml and the second
    # would silently win for every route in the first.
    assert app != gate
    assert app == "ShopApp"
    assert gate == "ShopGate"


def test_a_hyphenated_client_name_still_makes_a_legal_qml_module_uri():
    """A QML module URI is dotted identifiers, and an entity name is not held to that.

    `synqt add entity <name> --type monitor` names its console client `<name>-console`,
    so every project with a monitor has a second client whose name carries a hyphen. The
    URI was built by upper-casing the first letter and keeping the rest, which turned
    `ops-console` into `WatchedOps-console`; Qt answers that with "invalid QML module
    URI. You cannot import this" at build time and the module is then not importable at
    run time. The project name has always been folded through `qml_uri` for exactly this
    reason, and the entity name was not.
    """
    config, _ = _config(clients=("app", "ops-console"))
    config["project"] = {"name": "watched"}
    console = appmodel.qml_uri_for(config, config["entities"][2])
    assert console == "WatchedOpsConsole"
    for uri in (appmodel.qml_uri_for(config, config["entities"][1]), console):
        assert re.fullmatch(r"[A-Za-z_][0-9A-Za-z_]*", uri), uri


def test_two_client_names_that_fold_to_one_uri_are_refused():
    """The per-client URI exists to stop a collision, and folding can reintroduce one.

    `admin-ui` and `admin_ui` are two entities, two directories and two build targets, and
    one QML module URI: punctuation is what the folding drops. Left alone, one module
    claims the other's `Main.qml` and the wrong page loads with nothing said about it,
    which is the failure the per-client URI was added to prevent in the first place.
    """
    config, _ = _config(clients=("admin-ui", "admin_ui"))
    config["project"] = {"name": "shop"}
    ok, messages = check.validate(config)
    assert not ok
    assert any("admin-ui" in m and "admin_ui" in m and "ShopAdminUi" in m
               for m in messages), messages
