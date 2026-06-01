// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#ifndef SYNQT_SECRETSERVICESTORE_H
#define SYNQT_SECRETSERVICESTORE_H

#include "securestore.h"

namespace SynQt {

/// The Linux store: the freedesktop Secret Service (`org.freedesktop.secrets`), which
/// gnome-keyring-daemon implements and KWallet bridges, reached through libsecret.
///
/// libsecret rather than raw D-Bus because the session-key negotiation that keeps a secret
/// off the bus in the clear is the library's whole job, and reimplementing it would buy
/// nothing but a way to get it wrong.
///
/// Two things about this platform are stated rather than worked around:
///
///  - **No per-application boundary.** Any process on the session bus can read any item; the
///    old per-app ACL concept is not exposed through the Secret Service. So this reports
///    Binding::User, and the documentation says so without softening it.
///  - **Nothing here ever prompts.** A read against a locked collection returns no secret
///    instead of asking for a password, because the read happens before the first frame and
///    a modal dialog there is a hang on a headless or SSH session. The visitor signs in
///    normally instead, which is the correct outcome for a keyring that is not open.
class SecretServiceStore : public SecureStore
{
public:
    bool isAvailable(QString *reason) const override;
    bool store(const QString &account, const QByteArray &secret, QString *error) override;
    bool load(const QString &account, QByteArray *secret, QString *error) override;
    bool erase(const QString &account, QString *error) override;
    Binding binding() const override;
    QString name() const override;
};

} // namespace SynQt

#endif // SYNQT_SECRETSERVICESTORE_H
