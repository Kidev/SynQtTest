// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#ifndef SYNQT_COOKIES_H
#define SYNQT_COOKIES_H

#include <QByteArray>
#include <QList>

namespace SynQt {

/// The value of one named cookie in a `Cookie` request header, or empty when it carries none.
///
/// A `Cookie` header is one line of `name=value` pairs separated by `; `, and reading a
/// single name out of it is a five-line loop that had been written three times: once for the
/// session cookie on the upgrade path, once for the OAuth state cookie, and once inline in
/// the sign-out route. They agreed, which is the only reason nothing had gone wrong yet;
/// what a third copy costs is that a correction to one of them reaches two thirds of the
/// places it is needed.
///
/// The first match wins. A browser sends one value per name, and a caller that sends several
/// is choosing which of its own cookies is read rather than reaching anything else.
inline QByteArray cookieValue(const QByteArray &cookieHeader, const QByteArray &name)
{
    const QByteArray prefix{name + "="};
    const QList<QByteArray> parts{cookieHeader.split(';')};
    for (QByteArray part : parts) {
        part = part.trimmed();
        if (part.startsWith(prefix)) {
            return part.mid(prefix.size());
        }
    }
    return {};
}

} // namespace SynQt

#endif // SYNQT_COOKIES_H
