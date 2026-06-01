// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#include "credentialmanagerstore.h"

#include <QCoreApplication>

#include <qt_windows.h>

#include <wincred.h>

namespace SynQt {

namespace {

/// The target name a human sees in Credential Manager. Readable on purpose: finding this
/// entry and deleting it is one of the reasons for using the OS store at all.
QString targetName(const QString &account)
{
    const QString application{QCoreApplication::applicationName()};
    return QStringLiteral("SynQt:%1:%2")
        .arg(application.isEmpty() ? QStringLiteral("app") : application, account);
}

/// What the blob may grow to. CRED_MAX_CREDENTIAL_BLOB_SIZE is 2560 bytes; the budget is far
/// below it and checked, so a future field cannot quietly push the payload past a limit that
/// would then fail at the write, on somebody else's machine, months from now.
constexpr qsizetype kMaxBlob{512};

QString describe(DWORD code)
{
    LPWSTR text{nullptr};
    const DWORD length{FormatMessageW(
        FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM
            | FORMAT_MESSAGE_IGNORE_INSERTS,
        nullptr, code, 0, reinterpret_cast<LPWSTR>(&text), 0, nullptr)};
    if (length == 0 || text == nullptr) {
        return QStringLiteral("Windows error %1").arg(static_cast<uint>(code));
    }
    const QString message{QString::fromWCharArray(text, static_cast<qsizetype>(length))
                              .trimmed()};
    LocalFree(text);
    return message;
}

} // namespace

bool CredentialManagerStore::isAvailable(QString *reason) const
{
    // Always, on a normal interactive logon. A service or session-0 context has no
    // credential set of its own, and the API says so at the first call rather than through a
    // probe, so that is where it is reported from.
    Q_UNUSED(reason);
    return true;
}

bool CredentialManagerStore::store(const QString &account, const QByteArray &secret,
                                   QString *error)
{
    if (secret.size() > kMaxBlob) {
        if (error) {
            *error = QStringLiteral("the credential is larger than SynQt's %1-byte budget")
                         .arg(kMaxBlob);
        }
        return false;
    }
    const QString target{targetName(account)};
    QList<wchar_t> targetBuffer(target.size() + 1, L'\0');
    target.toWCharArray(targetBuffer.data());
    QList<wchar_t> userBuffer(account.size() + 1, L'\0');
    account.toWCharArray(userBuffer.data());

    CREDENTIALW credential{};
    credential.Type = CRED_TYPE_GENERIC;
    credential.TargetName = targetBuffer.data();
    credential.UserName = userBuffer.data();
    credential.CredentialBlobSize = static_cast<DWORD>(secret.size());
    credential.CredentialBlob = reinterpret_cast<LPBYTE>(const_cast<char *>(secret.data()));
    // This machine, and never CRED_PERSIST_ENTERPRISE: see the note on the class.
    credential.Persist = CRED_PERSIST_LOCAL_MACHINE;

    if (CredWriteW(&credential, 0) == FALSE) {
        if (error) {
            *error = describe(GetLastError());
        }
        return false;
    }
    return true;
}

bool CredentialManagerStore::load(const QString &account, QByteArray *secret, QString *error)
{
    const QString target{targetName(account)};
    QList<wchar_t> targetBuffer(target.size() + 1, L'\0');
    target.toWCharArray(targetBuffer.data());

    PCREDENTIALW found{nullptr};
    if (CredReadW(targetBuffer.data(), CRED_TYPE_GENERIC, 0, &found) == FALSE) {
        const DWORD code{GetLastError()};
        if (code != ERROR_NOT_FOUND && error) {
            // ERROR_NO_SUCH_LOGON_SESSION lands here: a service context has no credential
            // set, which means the same thing to the client as nothing being stored.
            *error = describe(code);
        }
        return false;  // nothing stored: the ordinary first launch
    }
    bool ok{false};
    if (found->CredentialBlob != nullptr && found->CredentialBlobSize > 0 && secret != nullptr) {
        *secret = QByteArray{reinterpret_cast<const char *>(found->CredentialBlob),
                             static_cast<qsizetype>(found->CredentialBlobSize)};
        ok = true;
    }
    CredFree(found);
    return ok;
}

bool CredentialManagerStore::erase(const QString &account, QString *error)
{
    const QString target{targetName(account)};
    QList<wchar_t> targetBuffer(target.size() + 1, L'\0');
    target.toWCharArray(targetBuffer.data());

    if (CredDeleteW(targetBuffer.data(), CRED_TYPE_GENERIC, 0) == FALSE) {
        const DWORD code{GetLastError()};
        if (code == ERROR_NOT_FOUND) {
            return true;  // nothing to delete is a success
        }
        if (error) {
            *error = describe(code);
        }
        return false;
    }
    return true;
}

SecureStore::Binding CredentialManagerStore::binding() const
{
    // User, and not more. DPAPI protects the blob against another user and against an
    // offline disk, and against nothing running as this user.
    return Binding::User;
}

QString CredentialManagerStore::name() const
{
    return QStringLiteral("Credential Manager");
}

} // namespace SynQt
