// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#include "pollingdispatcher.h"

#include <QByteArray>
#include <QtGlobal>

namespace SynQt {

void preferPollingEventDispatcher()
{
    // Only when nothing has been said, so an operator who wants GLib back gets it, and a
    // container that already sets the variable is not overridden. isSet rather than isEmpty:
    // an empty QT_NO_GLIB is Qt's own spelling of "use GLib", and honouring it is the only
    // way this can be turned off at all.
    if (qEnvironmentVariableIsSet("QT_NO_GLIB")) {
        return;
    }
    // Everywhere but Linux this is already true and the variable is read by nothing, so it
    // is set unconditionally rather than guarded by a platform check: one behaviour to
    // reason about, and no #if around the only line that does anything.
    qputenv("QT_NO_GLIB", "1");
}

} // namespace SynQt
