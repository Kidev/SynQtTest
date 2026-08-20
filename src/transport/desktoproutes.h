// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#ifndef SYNQT_DESKTOPROUTES_H
#define SYNQT_DESKTOPROUTES_H

#include <QString>

namespace SynQt {

/// The two routes a native client speaks to, derived from the project's login route.
///
/// A desktop sign-in ends at `<login>/claim`, and staying signed in spends a credential at
/// `<login>/device`. Both hang off the login route so that renaming the login renames all
/// three, and both are computed on two sides of the network: the edge to decide where to
/// serve them, the client to decide where to POST.
///
/// One definition, because two would be an agreement rather than a fact. It was two: the
/// same six-line helper and the same two leaf strings, written once in the client runtime
/// and once on the edge. Nothing had gone wrong, and nothing would have until somebody
/// changed one of the four literals, at which point the desktop sign-in would fail with a
/// 404 from a route the edge is certain it serves.
inline QString desktopRoute(const QString &loginRoute, QLatin1StringView leaf)
{
    QString route{loginRoute};
    while (route.endsWith(QLatin1Char('/'))) {
        route.chop(1);
    }
    return route + leaf;
}

/// Where a native client exchanges its claim code for the session it stands for.
inline QString desktopClaimRoute(const QString &loginRoute)
{
    return desktopRoute(loginRoute, QLatin1StringView{"/claim"});
}

/// Where a native client spends a stored device credential for a fresh session.
inline QString desktopDeviceRoute(const QString &loginRoute)
{
    return desktopRoute(loginRoute, QLatin1StringView{"/device"});
}

} // namespace SynQt

#endif // SYNQT_DESKTOPROUTES_H
