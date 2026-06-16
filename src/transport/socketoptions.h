// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#ifndef SYNQT_SOCKETOPTIONS_H
#define SYNQT_SOCKETOPTIONS_H

#include <QtCore/qglobal.h>

QT_BEGIN_NAMESPACE
class QAbstractSocket;
QT_END_NAMESPACE

namespace SynQt {

/// Turn off Nagle's algorithm on a connected TCP socket.
///
/// Every socket SynQt keeps open carries a push protocol: small frames, sent when
/// something happened, with no bulk transfer to batch them into. That is the workload
/// Nagle penalizes. It holds a small segment back until the previous one is acknowledged,
/// and the peer's delayed-ACK timer holds that acknowledgement back in turn, so two
/// mechanisms that are each reasonable alone can add tens of milliseconds to a frame that
/// was ready to leave immediately.
///
/// Qt already does this for a socket QWebSocket dials out on, but not for one a server
/// accepts, and the accepted socket is the one an edge pushes every property change and
/// every model row down. It is set here on both, and on mesh links in both directions,
/// so no SynQt socket is left with it on.
///
/// A no-op on a socket that is not connected yet: the option needs a socket engine
/// underneath it, so call this once the socket is connected (from an accept handler, or
/// from QAbstractSocket::connected on a socket being dialled out).
void disableNagle(QAbstractSocket *socket);

} // namespace SynQt

#endif // SYNQT_SOCKETOPTIONS_H
