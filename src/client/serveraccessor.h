// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#ifndef SYNQT_SERVERACCESSOR_H
#define SYNQT_SERVERACCESSOR_H

#include "synclientconfig.h"

#include <QHash>
#include <QList>
#include <QQmlPropertyMap>

QT_BEGIN_NAMESPACE
class QRemoteObjectNode;
QT_END_NAMESPACE

namespace SynQt {

class ConsumerBase;

/// The client's handle on what it consumes: the connect point of every owner it reaches,
/// by that owner's name, as a live Replica behind its consumer facade. Replicas are
/// acquired in C++ (the QtRO QML Node type cannot take an externally connected transport).
///
/// The generated main puts each one in QML scope under its owner's name, and the one
/// belonging to the edge under \qmlServer as well, which is the name a browser client
/// normally writes: it reaches exactly one edge and nothing else.
///
/// Each facade is built here, at construction, rather than when a link first comes up. A
/// binding written against `Server` is evaluated on the first frame, and a name that
/// resolves to nothing until the handshake finishes is a binding that never runs again.
///
/// \sa \ref qmlserver "the Server accessor page"
class ServerAccessor : public QQmlPropertyMap
{
    Q_OBJECT

public:
    explicit ServerAccessor(QList<ClientConnectPoint> connectPoints,
                            QObject *parent = nullptr);

    /// Acquire the Replica of each consumed connect point on the given node and present
    /// it by name. Called on every (re)connect so bindings resume on a fresh link.
    void bindNode(QRemoteObjectNode *node);

    /// The object QML reaches one connect point through, or nullptr when this client
    /// consumes no point of that name. Stable for the life of the client wherever the
    /// contract has a consumer facade, which is every contract the build generates.
    QObject *point(const QString &name) const;

private slots:
    /// Re-publish a Replica once its QtRO handshake completes, so QML bindings re-evaluate.
    void onReplicaInitialized();

private:
    QList<ClientConnectPoint> m_connectPoints;
    QHash<QObject *, QString> m_pending; ///< raw replica -> connect-point name (fallback path)
    QHash<QString, ConsumerBase *> m_facades; ///< owner name -> stable facade
};

} // namespace SynQt

#endif // SYNQT_SERVERACCESSOR_H
