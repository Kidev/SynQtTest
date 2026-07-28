// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#ifndef SYNQT_SESSIONSTATESOURCE_H
#define SYNQT_SESSIONSTATESOURCE_H

#include "rep_sessionstate_source.h"

#include <QObject>

namespace SynQt {

class Caller;

/// The web edge's own Source for the framework-supplied SessionState connect point: who
/// the visitor on this connection is, published to the client that is them.
///
/// WebEdge hosts one per accepted connection, exactly the way it hosts a per-caller
/// application connect point, over that connection's own Caller. The Caller is the whole
/// implementation: it already resolves the live session record and it already follows the
/// credential rotation a scope change makes, so this class is the step that turns what it
/// answers into something the client can bind to.
///
/// It publishes nothing a caller could not already ask for about itself, and nothing at
/// all about anybody else: the scope this session was granted and the normalized identity
/// behind it, which is the same object the mapping hook returned. The session credential
/// stays where it was; the browser is holding its own copy in a cookie it cannot read, and
/// putting it on a connect point would hand page script the one string that IS the visitor.
class SessionStateSource : public SessionStateSimpleSource
{
    Q_OBJECT

public:
    /// caller is this connection's own and must never be shared with another connection's
    /// Source; it is expected to outlive this object (WebEdge parents it here).
    explicit SessionStateSource(Caller *caller, QObject *parent = nullptr);

private:
    void publish();

    Caller *m_caller;
};

} // namespace SynQt

#endif // SYNQT_SESSIONSTATESOURCE_H
