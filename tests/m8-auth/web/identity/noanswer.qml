// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

import SynQt

// A mapping hook that loads but answers nothing: no scopeFor at all. There used to be a
// `return QStringLiteral("user")` at the end of mapScope for exactly this case, so a
// project whose hook was renamed or mistyped signed everybody in as an authenticated user.
IdentityMapping {
}
