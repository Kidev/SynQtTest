// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#ifndef SYNQT_SQLSUPPORT_H
#define SYNQT_SQLSUPPORT_H

#include "ipersistenceprovider.h"

#include <QString>
#include <QStringList>
#include <QVariantList>

QT_BEGIN_NAMESPACE
class QSqlDatabase;
QT_END_NAMESPACE

namespace SynQt {

/// \file
/// Statement execution and migration logic shared by every relational provider (sqlite,
/// postgres, mysql). All of them bind parameters through QSqlQuery::prepare +
/// addBindValue (the `?` placeholder is portable across Qt SQL drivers), so no provider is
/// ever handed concatenated SQL. Kept as free functions so the providers stay parallel
/// final classes rather than sharing a base.
///
/// sqlite had its own copy of both of these, character for character apart from one line:
/// its runStatement wrote `lastInsertId()` through whether or not the driver had one to
/// give, so an UPDATE came back carrying an invalid QVariant where the other two providers
/// left the field alone. That is the shape of what a second copy costs, and it is why
/// there is one now.

/// Prepare + bind + run one statement. collectRows gathers a column-name map per row for a
/// SELECT; otherwise it reports affected rows and the last insert id. Errors are returned in
/// the DbResult, never thrown.
DbResult runStatement(QSqlDatabase &db, const QString &sql, const QVariantList &params,
                      bool collectRows);

/// Apply any migration steps not yet recorded in synqt_migrations, in order, inside one
/// transaction, then record the new version. Re-running is a no-op. Returns false + *error
/// if a step fails (and rolls the batch back).
bool applyMigrations(QSqlDatabase &db, const QStringList &steps, QString *error);

} // namespace SynQt

#endif // SYNQT_SQLSUPPORT_H
