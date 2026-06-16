// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#include "iothreadpool.h"

#include <QString>
#include <QThread>

#include <utility>

namespace SynQt {

IoThreadPool::IoThreadPool(int threadCount, QObject *parent)
    : QObject{parent}
{
    const int count{qMax(1, threadCount)};
    m_threads.reserve(count);
    for (int index{0}; index < count; ++index) {
        QThread *thread{new QThread{this}};
        // Named so a stack in a profiler or a debugger says which socket thread it is,
        // rather than a row of identical unnamed threads.
        thread->setObjectName(QStringLiteral("SynQt io %1").arg(index));
        thread->start();
        m_threads.append(thread);
    }
}

/// Stop every thread before the base destructor gets to delete them, because deleting a
/// running QThread is fatal. Anything still living on one of these threads must already be
/// gone by here; the entity that filled the pool is what owns that order.
IoThreadPool::~IoThreadPool()
{
    for (QThread *thread : std::as_const(m_threads)) {
        thread->quit();
    }
    for (QThread *thread : std::as_const(m_threads)) {
        thread->wait();
    }
}

int IoThreadPool::threadCount() const
{
    return static_cast<int>(m_threads.size());
}

QThread *IoThreadPool::threadAt(int index) const
{
    return m_threads.value(index, nullptr);
}

QThread *IoThreadPool::nextThread()
{
    QThread *thread{m_threads.at(m_next)};
    m_next = (m_next + 1) % static_cast<int>(m_threads.size());
    return thread;
}

} // namespace SynQt
