// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#ifndef SYNQT_POOLEDSQLPROVIDER_H
#define SYNQT_POOLEDSQLPROVIDER_H

#include "ipersistenceprovider.h"
#include "sqlconnectionpool.h"

#include <memory>

QT_BEGIN_NAMESPACE
class QSqlDatabase;
QT_END_NAMESPACE

namespace SynQt {

/// Whether an `sslmode` is one that verifies the engine's certificate.
///
/// Both external providers ask this and neither is the authority on it, so it lives beside
/// the pool they share rather than twice in two anonymous namespaces.
inline bool isVerifiedSslMode(const QString &sslMode)
{
    return sslMode == QLatin1String("verify-ca") || sslMode == QLatin1String("verify-full");
}

/// What a relational provider that talks to an external engine over a connection pool is,
/// minus the engine.
///
/// The two that do (postgres, mysql) differ in exactly three places: the driver name, how a
/// connection is configured, and what counts as a secure enough connection to open at all.
/// Everything after that is the same work in the same order, and it was written out twice:
/// a transient lease per statement, a pinned lease for the span of a transaction, and a
/// migration on a lease of its own. Around a hundred and thirty lines, identical to the
/// character, in two files that would be corrected one at a time.
///
/// The three that differ stay on the subclass, which is why this is a base and not a
/// template: `connect()` is the provider's own (it decides whether to open at all, and with
/// what), and it calls openPool() when it has decided.
///
/// A `final` subclass on top of this keeps the devirtualized call sites the two providers
/// had before; nothing here is virtual that the interface did not already declare.
class PooledSqlProvider : public IPersistenceProvider
{
public:
    ~PooledSqlProvider() override;

    void disconnect() override;
    bool isHealthy() const override;
    DbResult query(const QString &sql, const QVariantList &params) override;
    DbResult exec(const QString &sql, const QVariantList &params) override;
    bool begin(QString *error) override;
    bool commit(QString *error) override;
    bool rollback(QString *error) override;
    bool migrate(const QStringList &steps, QString *error) override;

protected:
    /// Build the pool, open one connection to prove the configuration, and create the
    /// migrations table on it. \a configure is called for each connection the pool opens.
    ///
    /// Opening one now rather than lazily is what turns a wrong host or a wrong password
    /// into a refusal at start-up instead of into the first query a visitor makes.
    bool openPool(const QString &driver, SqlConnectionPool::Configure configure, int poolSize,
                  QString *error);

private:
    /// Run one statement on the pinned transaction lease when there is one, and on a
    /// transient lease otherwise, so concurrent callers outside a transaction each get
    /// their own connection.
    DbResult runOnLease(const QString &sql, const QVariantList &params, bool collectRows);

    // Declared before the lease below, and it has to be: members are destroyed in reverse,
    // so this order is what makes `m_txLease` release itself back into a pool that is still
    // there. Swapped, an entity destroyed mid-transaction would run ~Lease against a pool
    // that had already gone.
    std::unique_ptr<SqlConnectionPool> m_pool;
    SqlConnectionPool::Lease m_txLease;  ///< valid only while a transaction is open
    bool m_inTransaction{false};
};

} // namespace SynQt

#endif // SYNQT_POOLEDSQLPROVIDER_H
