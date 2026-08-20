// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#ifndef SYNQT_OBJECTTREE_H
#define SYNQT_OBJECTTREE_H

#include <QObject>

namespace SynQt {

/// Whether `candidate` already sits somewhere under `ancestor`.
///
/// Asked before adopting a socket. An accepted browser connection is two objects, the
/// QWebSocket and the raw socket under it, and which of them owns the other depends on how
/// the connection was made: on some paths Qt has already made the raw socket a child of the
/// QWebSocket, and on others nobody owns it at all. Reparenting it in the first case takes
/// it away from an owner that is counting on having it; leaving it alone in the second leaks
/// the whole connection. So the adoption is conditional, and this is the condition.
///
/// It lives here because both places that ask it are adopting the same socket for the same
/// reason: `SocketChannel` when it gathers a connection to carry to an IO thread, and the
/// web edge when the link has no channel to gather it into. They were the same eight lines
/// twice, and the second copy carried a comment pointing at the first.
inline bool isUnder(const QObject *candidate, const QObject *ancestor)
{
    for (const QObject *walk{candidate}; walk != nullptr; walk = walk->parent()) {
        if (walk == ancestor) {
            return true;
        }
    }
    return false;
}

} // namespace SynQt

#endif // SYNQT_OBJECTTREE_H
