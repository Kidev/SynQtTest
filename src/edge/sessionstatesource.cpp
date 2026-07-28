// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#include "sessionstatesource.h"

#include "caller.h"

#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonValue>
#include <QVariantMap>

namespace SynQt {

namespace {
constexpr auto kScope{"scope"};
constexpr auto kIdentity{"identity"};
}

SessionStateSource::SessionStateSource(Caller *caller, QObject *parent)
    : SessionStateSimpleSource{parent}
    , m_caller{caller}
{
    // Published now rather than on a signal, because the first thing a client does with
    // this is read it: the connection has just been accepted for a session that already
    // has its scope and its identity, and there is no later event that would announce
    // either of them.
    publish();
    // A rotation is a privilege change and the only thing that causes one, so this is
    // every way a live session's scope moves under a connection that is already up
    // (Caller.setScope in a slot is the ordinary one). The Caller has already followed the
    // rotation to the new credential by the time this runs.
    connect(m_caller, &Caller::scopeChanged, this, &SessionStateSource::publish);
}

void SessionStateSource::publish()
{
    // A connection the edge holds no session for is one it has nothing to say about, and
    // saying so as an empty scope would be worse than silence: the client would take "" for
    // its granted scope and stop holding even the default it started at. The property is
    // left unset and the client keeps its own answer.
    if (!m_caller->hasSession()) {
        return;
    }
    QJsonObject state;
    state.insert(QLatin1String{kScope}, m_caller->scope());
    // Null, not an empty object, while anonymous: `Session.identity` is documented as
    // null when nobody is signed in, and QML tells the two apart (`!Session.identity` is
    // how an app asks, and an empty object is truthy).
    const QVariantMap identity{m_caller->identity().toMap()};
    state.insert(QLatin1String{kIdentity},
                 identity.isEmpty() ? QJsonValue{QJsonValue::Null}
                                    : QJsonValue{QJsonObject::fromVariantMap(identity)});
    setSession(QString::fromUtf8(
        QJsonDocument{state}.toJson(QJsonDocument::Compact)));
}

} // namespace SynQt
