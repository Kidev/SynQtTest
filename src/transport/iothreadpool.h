// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#ifndef SYNQT_IOTHREADPOOL_H
#define SYNQT_IOTHREADPOOL_H

#include <QList>
#include <QObject>

QT_BEGIN_NAMESPACE
class QThread;
QT_END_NAMESPACE

namespace SynQt {

/// The threads a threaded entity spreads its accepted sockets across.
///
/// Every socket still belongs to exactly one thread for its whole life, and the object
/// graph a caller's traffic is decoded into (the QtRO host, the Sources, the QML engine)
/// stays where it was: only the socket moves. That is what makes this safe to bolt onto
/// an entity without changing the programming model, and it is why the pool hands out
/// threads rather than tasks.
///
/// These are real QThreads running exec(), not QThreadPool or QtConcurrent workers. A
/// QWebSocket needs an event loop on its own thread for its socket notifiers to fire, and
/// a pool worker has none, so a socket moved onto one would simply stop delivering with
/// nothing reporting an error.
class IoThreadPool : public QObject
{
    Q_OBJECT

public:
    /// Start `threadCount` threads (at least one; a smaller number is raised to one, since
    /// a pool of none could answer nextThread() with nothing).
    explicit IoThreadPool(int threadCount, QObject *parent = nullptr);
    ~IoThreadPool() override;

    int threadCount() const;
    QThread *threadAt(int index) const;

    /// The thread the next socket goes on, round robin.
    ///
    /// Round robin rather than least-loaded on purpose: what a connection costs is not
    /// known when it is accepted, tracking it would need a counter every close has to
    /// find its way back to, and an even spread is what a large number of similar browser
    /// connections wants anyway.
    QThread *nextThread();

private:
    QList<QThread *> m_threads;
    int m_next{0};
};

} // namespace SynQt

#endif // SYNQT_IOTHREADPOOL_H
