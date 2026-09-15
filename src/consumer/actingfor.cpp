// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#include "actingfor.h"

#include "tracescope.h"

#include <QMetaObject>

namespace SynQt {

namespace {

QPointer<QObject> &acting()
{
    // Per thread, though one entity is one event loop and every slot runs on it. The cost
    // is a thread-local lookup on a path that already crosses the network, and what it buys
    // is that "whose session does an outbound call carry" stops being a fact about how the
    // runtime happens to be scheduled today. A plain static holding that answer is right
    // until the first slot runs somewhere else, and wrong in the direction where one
    // caller's session travels under another caller's call.
    //
    // Not a QObject, so none of the caveat in WebSocketTransport's thread_local applies: a
    // QPointer whose target is gone is already null and destroying it does nothing.
    static thread_local QPointer<QObject> caller;
    return caller;
}

} // namespace

ActingFor::ActingFor(QObject *caller)
    : m_displaced{acting()}
{
    acting() = caller;
}

ActingFor::~ActingFor()
{
    acting() = m_displaced;
}

QVariantMap ActingFor::current()
{
    QObject *caller{acting().data()};
    if (!caller) {
        QVariantMap session;
        withTrace(session);
        return session;
    }
    // Asked for here rather than on the way in, so an inbound slot that calls nothing out
    // pays nothing for this: the lookup happens only when there is an outbound call to
    // carry the answer. By name, because the generated code that opens an ActingFor has no
    // way to include caller.h, and a Caller is the only thing that answers to this.
    QVariantMap session;
    QMetaObject::invokeMethod(caller, "forwardedSession", Qt::DirectConnection,
                              Q_RETURN_ARG(QVariantMap, session));
    withTrace(session);
    return session;
}

void ActingFor::withTrace(QVariantMap &session)
{
    // The trace rides along with the session because the session is already the thing that
    // travels down the chain, and a second channel for it would be a second thing to
    // forget. It is not part of the session: nothing authorizes anything by it, and a
    // Caller that ignores the map (a browser's) ignores this with it. Taken from the
    // thread and not from the caller, because the work that makes an outbound call is
    // not always answering somebody: a continuation acts for nobody and still belongs to
    // the click that started it.
    TraceScope::current().writeTo(session);
}

} // namespace SynQt
