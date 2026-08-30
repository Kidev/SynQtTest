// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#ifndef SYNQT_POSTGRESPROVIDER_H
#define SYNQT_POSTGRESPROVIDER_H

#include "pooledsqlprovider.h"
#include "providerconfig.h"

namespace SynQt {

/// A third-party relational provider over the QPSQL driver, implementing the SAME
/// IPersistenceProvider interface as sqlite, so the connect point Source is unchanged when
/// an entity switches to PostgreSQL. It connects over verified TLS (sslmode=verify-full
/// against a configured CA) and REFUSES a plaintext or unverified connection in release;
/// only dev on localhost may relax that. Credentials come from the entity env only and are
/// never logged. Parameters are always bound (`?` placeholders), never concatenated.
///
/// Connections are drawn from a bounded SqlConnectionPool (poolSize), so concurrent reads
/// scale to the pool cap; a transaction pins one connection for its span. The connection is
/// owned on the entity's thread (Qt SQL requires it). All of that is PooledSqlProvider's,
/// which this shares with the mysql provider; what is Postgres's own is the driver name,
/// how a connection is configured, and what it will refuse to open.
class PostgresProvider final : public PooledSqlProvider
{
public:
    explicit PostgresProvider(ProviderConfig config);
    ~PostgresProvider() override;

    bool connect(QString *error) override;
    QString name() const override;

    /// The insecure-connection guard, exposed for testing: true when this config must be
    /// refused (release + a non-loopback host + an unverified sslmode).
    bool refusesInsecure() const;

private:
    ProviderConfig m_config;
};

} // namespace SynQt

#endif // SYNQT_POSTGRESPROVIDER_H
