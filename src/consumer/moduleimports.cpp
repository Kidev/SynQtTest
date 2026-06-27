// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#include "moduleimports.h"

#include <QQmlEngine>

namespace SynQt {

void registerModuleImports()
{
    // Called once per process however many times it is asked for: the generated entity main
    // makes this call, and so does every generated contract registration (an entity has
    // several), each of them for the same process-wide type registry. Registering the same
    // import twice is not an error, it just leaves the engine two identical entries to walk
    // on every `import SynQt`.
    static bool registered{false};
    if (registered) {
        return;
    }
    registered = true;

    // QQmlModuleImportLatest for the version, which is what omitting the version in a
    // qmldir `import` line means. The alternative spelling, QQmlModuleImportAuto, asks
    // for QtQuick at the version SynQt itself was imported at; SynQt is 1.0 and QtQuick
    // has no 1.0, so that spelling fails the import rather than resolving it.
    qmlRegisterModuleImport("SynQt", 1, "QtQuick",
                            QQmlModuleImportLatest, QQmlModuleImportLatest);
}

} // namespace SynQt
