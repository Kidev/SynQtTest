// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#include "serveraccessor.h"

#include "replicaregistry.h"

#include "consumerbase.h"
#include "consumerfactory.h"

#include <QRemoteObjectNode>

#include <utility>

namespace SynQt {

ServerAccessor::ServerAccessor(QList<ClientConnectPoint> connectPoints, QObject *parent)
    : QQmlPropertyMap{this, parent}
    , m_connectPoints{std::move(connectPoints)}
{
    // Every facade up front, before any link exists. The generated main puts these objects
    // in QML scope by name, and QML evaluates a binding against a name once: `Server.total`
    // resolved against nothing on the first frame stays nothing, however well the link
    // comes up a moment later. A facade with no Replica yet reads as empty and starts
    // reporting the moment bindNode() hands it one.
    for (const ClientConnectPoint &connectPoint : std::as_const(m_connectPoints)) {
        ConsumerBase *facade{makeConsumer(connectPoint.contract)};
        if (facade != nullptr) {
            facade->setPoint(connectPoint.name);
            facade->setParent(this);
            m_facades.insert(connectPoint.name, facade);
            insert(connectPoint.name, QVariant::fromValue<QObject *>(facade));
        }
    }
}

QObject *ServerAccessor::point(const QString &name) const
{
    if (ConsumerBase *facade{m_facades.value(name)}) {
        return facade;
    }
    // No consumer facade registered for this contract (a Replica-only build): the raw
    // Replica is what there is, and only once a link has acquired one.
    return value(name).value<QObject *>();
}

void ServerAccessor::bindNode(QRemoteObjectNode *node)
{
    for (const ClientConnectPoint &connectPoint : std::as_const(m_connectPoints)) {
        // Acquire a typed Replica when the contract's factory is registered (typed
        // Replicas carry their API and sync reliably, including in the browser), else a
        // dynamic Replica. The Replica is parented to the node and replaced on reconnect.
        QObject *replica{acquireReplica(node, connectPoint.contract, connectPoint.name)};
        replica->setParent(node);
        const QString name{connectPoint.name};

        // The facade forwards properties, models and signals, adds returning-slot promises,
        // and feeds the `<Contract>.on<Signal>` attached handlers. Built in the constructor
        // and kept, so a reconnect hands the same object a fresh Replica and every QML
        // binding against it holds.
        if (ConsumerBase *existing{m_facades.value(name)}) {
            existing->setReplica(replica);
            continue;
        }

        // No facade registered for this contract (a Replica-only build): expose the raw
        // Replica, re-notifying on initialization so QML bindings re-evaluate.
        insert(name, QVariant::fromValue<QObject *>(replica));
        connect(replica, SIGNAL(initialized()), this, SLOT(onReplicaInitialized()));
        m_pending.insert(replica, name);
    }
}

void ServerAccessor::onReplicaInitialized()
{
    QObject *replica{sender()};
    const QString name{m_pending.value(replica)};
    if (!name.isEmpty()) {
        insert(name, QVariant::fromValue<QObject *>(replica));
    }
}

} // namespace SynQt
