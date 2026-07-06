// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#ifndef SYNQT_LOG_H
#define SYNQT_LOG_H

#include <QObject>
#include <QVariantMap>

namespace SynQt {

/// What an entity has to say about itself, in its own QML: `Log.info("started", {items: 3})`.
///
/// The framework records what it can see, which is links coming up, callers being refused
/// and calls crossing. What it cannot see is why an entity did what it did, and that is
/// the half an operator is usually looking for. This is where an entity says it.
///
/// Installed for every type, unlike `Db` or `Cache`. Those exist because a type has an
/// engine behind it and are absent where there is none; every entity has something to say,
/// so every entity has this.
///
/// A message and a map, not a formatted sentence. The record is filtered and searched by
/// whoever reads it, and `Log.info("saved " + count + " rows")` makes both a substring
/// hunt where `Log.info("saved rows", {rows: count})` does not.
///
/// What an entity may not do is say it is a different entity: the runtime stamps the name
/// on the way out, and an `entity` key in the attributes is not read. An entity's own
/// record of itself is the one thing in the system it cannot forge.
class Log : public QObject
{
    Q_OBJECT

public:
    explicit Log(QObject *parent = nullptr);

    Q_INVOKABLE void debug(const QString &message,
                           const QVariantMap &attributes = QVariantMap());
    Q_INVOKABLE void info(const QString &message,
                          const QVariantMap &attributes = QVariantMap());
    Q_INVOKABLE void warn(const QString &message,
                          const QVariantMap &attributes = QVariantMap());
    Q_INVOKABLE void error(const QString &message,
                           const QVariantMap &attributes = QVariantMap());
};

} // namespace SynQt

#endif // SYNQT_LOG_H
