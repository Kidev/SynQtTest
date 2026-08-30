// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#include "sqlsupport.h"

#include <QSqlDatabase>
#include <QSqlError>
#include <QSqlQuery>
#include <QSqlRecord>
#include <QVariantMap>

namespace SynQt {

DbResult runStatement(QSqlDatabase &db, const QString &sql, const QVariantList &params,
                      bool collectRows)
{
    QSqlQuery statement{db};
    if (!statement.prepare(sql)) {
        return DbResult::failure(statement.lastError().text());
    }
    for (const QVariant &value : params) {
        statement.addBindValue(value);
    }
    if (!statement.exec()) {
        return DbResult::failure(statement.lastError().text());
    }
    DbResult result;
    result.ok = true;
    if (collectRows) {
        while (statement.next()) {
            const QSqlRecord record{statement.record()};
            QVariantMap row;
            for (int column{0}; column < record.count(); ++column) {
                row.insert(record.fieldName(column), statement.value(column));
            }
            result.rows.append(row);
        }
    } else {
        result.affected = statement.numRowsAffected();
        const QVariant insertId{statement.lastInsertId()};
        if (insertId.isValid()) {
            result.insertId = insertId;
        }
    }
    return result;
}

bool applyMigrations(QSqlDatabase &db, const QStringList &steps, QString *error)
{
    const DbResult versionResult{
        runStatement(db, QStringLiteral("SELECT version FROM synqt_migrations"), {}, true)};
    if (!versionResult.ok) {
        if (error != nullptr) {
            *error = versionResult.error;
        }
        return false;
    }
    int applied{0};
    if (!versionResult.rows.isEmpty()) {
        applied = versionResult.rows.first().toMap().value(QStringLiteral("version")).toInt();
    }
    if (applied >= steps.size()) {
        return true;  // nothing new to apply; re-running migrate is a no-op
    }
    if (!db.transaction()) {
        if (error != nullptr) {
            *error = db.lastError().text();
        }
        return false;
    }
    for (int step{applied}; step < steps.size(); ++step) {
        const DbResult stepResult{runStatement(db, steps.at(step), {}, false)};
        if (!stepResult.ok) {
            db.rollback();
            if (error != nullptr) {
                // Which step, not only what the engine said. A schema is a list of
                // statements and the engine's message names none of them, so without the
                // number the reader is left counting entries in `schema:` by hand.
                *error = QStringLiteral("migration step %1 failed: %2")
                             .arg(step + 1)
                             .arg(stepResult.error);
            }
            return false;
        }
    }
    runStatement(db, QStringLiteral("DELETE FROM synqt_migrations"), {}, false);
    runStatement(db, QStringLiteral("INSERT INTO synqt_migrations(version) VALUES(?)"),
                 {steps.size()}, false);
    return db.commit();
}

} // namespace SynQt
