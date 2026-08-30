// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#include "sqliteprovider.h"

#include "sqlsupport.h"

#include <QSqlError>
#include <QSqlQuery>
#include <QStringList>
#include <QUuid>

#include <utility>

namespace SynQt {

namespace {

/// The journal mode to ask SQLite for, given what the topology asked for.
///
/// SQLite takes a PRAGMA value as a bare word, so this is the one setting on this provider
/// that reaches the engine as SQL text rather than as a bound parameter. It comes from
/// `synqt.yaml` and not from a caller, so this is not an injection anybody can reach today;
/// it is refused anyway, because "a string from configuration is concatenated into SQL" is
/// a sentence that should not be true of this file at all, and a typo in a journal mode is
/// worth a message rather than a statement SQLite silently declines.
QString journalModeOrDefault(const QString &requested)
{
    static const QStringList modes{QStringLiteral("delete"), QStringLiteral("truncate"),
                                   QStringLiteral("persist"), QStringLiteral("memory"),
                                   QStringLiteral("wal"), QStringLiteral("off")};
    const QString lowered{requested.toLower()};
    if (modes.contains(lowered)) {
        return lowered;
    }
    qWarning("SynQt: '%s' is not a SQLite journal mode; using WAL. One of: %s",
             qUtf8Printable(requested), qUtf8Printable(modes.join(QStringLiteral(", "))));
    return QStringLiteral("wal");
}

} // namespace

SqliteProvider::SqliteProvider(ProviderConfig config)
    : m_config{std::move(config)}
    , m_connectionName{QStringLiteral("synqt-sqlite-%1")
                           .arg(QUuid::createUuid().toString(QUuid::WithoutBraces))}
{
}

SqliteProvider::~SqliteProvider()
{
    disconnect();
}

QString SqliteProvider::name() const
{
    return QStringLiteral("sqlite");
}

bool SqliteProvider::connect(QString *error)
{
    m_db = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), m_connectionName);
    m_db.setDatabaseName(m_config.file);
    // A busy database retries up to the timeout rather than failing immediately.
    m_db.setConnectOptions(
        QStringLiteral("QSQLITE_BUSY_TIMEOUT=%1").arg(m_config.busyTimeoutMs));
    if (!m_db.open()) {
        if (error) {
            *error = m_db.lastError().text();
        }
        return false;
    }
    // WAL journalling (better concurrency: readers do not block a writer) and enforced
    // foreign keys.
    QSqlQuery pragma{m_db};
    pragma.exec(QStringLiteral("PRAGMA journal_mode=%1")
                    .arg(journalModeOrDefault(m_config.journalMode)));
    pragma.exec(QStringLiteral("PRAGMA foreign_keys=ON"));
    if (!runStatement(m_db,
                      QStringLiteral("CREATE TABLE IF NOT EXISTS synqt_migrations "
                                     "(version INTEGER NOT NULL)"),
                      {}, false)
             .ok) {
        if (error) {
            *error = QStringLiteral("failed to create the migrations table");
        }
        return false;
    }
    return true;
}

void SqliteProvider::disconnect()
{
    if (m_db.isOpen()) {
        m_db.close();
    }
    m_db = QSqlDatabase{};
    if (QSqlDatabase::contains(m_connectionName)) {
        QSqlDatabase::removeDatabase(m_connectionName);
    }
}

bool SqliteProvider::isHealthy() const
{
    return m_db.isOpen() && m_db.isValid();
}

DbResult SqliteProvider::query(const QString &sql, const QVariantList &params)
{
    if (!m_db.isOpen()) {
        return DbResult::failure(QStringLiteral("provider not connected"));
    }
    return runStatement(m_db, sql, params, true);
}

DbResult SqliteProvider::exec(const QString &sql, const QVariantList &params)
{
    if (!m_db.isOpen()) {
        return DbResult::failure(QStringLiteral("provider not connected"));
    }
    return runStatement(m_db, sql, params, false);
}

bool SqliteProvider::begin(QString *error)
{
    if (!m_db.transaction()) {
        if (error) {
            *error = m_db.lastError().text();
        }
        return false;
    }
    return true;
}

bool SqliteProvider::commit(QString *error)
{
    if (!m_db.commit()) {
        if (error) {
            *error = m_db.lastError().text();
        }
        return false;
    }
    return true;
}

bool SqliteProvider::rollback(QString *error)
{
    if (!m_db.rollback()) {
        if (error) {
            *error = m_db.lastError().text();
        }
        return false;
    }
    return true;
}

bool SqliteProvider::migrate(const QStringList &steps, QString *error)
{
    return applyMigrations(m_db, steps, error);
}

} // namespace SynQt
