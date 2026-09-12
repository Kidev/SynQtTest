#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0

# Generate throwaway certificates for the M3 mesh acceptance test into $1:
#   ca         - the project private CA
#   alpha      - owner entity cert (SAN DNS:alpha), signed by ca
#   beta       - consumer entity cert (SAN DNS:beta), signed by ca
#   foreignca  - an unrelated CA
#   rogue      - a cert signed by foreignca (the "wrong CA" case)
#   impostor   - a CA-signed leaf for localhost/127.0.0.1 (the edge's browser-facing
#                profile), so an owner presenting it matches the address and not a name
#
# The profiles come from tests/lib/mesh-certs.sh, which mirrors what `synqt mesh cert`
# issues. These are TEST certificates only: they live under build/ (git-ignored) and are
# never committed; no production mesh CA key is created here (see docs/security.md).

set -euo pipefail

# shellcheck source=../lib/mesh-certs.sh
. "$(cd "$(dirname "$0")/../lib" && pwd)/mesh-certs.sh"

OUT="${1:?usage: gen-certs.sh <output-dir>}"
mkdir -p "$OUT"
cd "$OUT"

if synqt_certs_current .profile ca.crt alpha.crt beta.crt foreignca.crt rogue.crt \
        impostor.crt; then
    exit 0
fi

synqt_gen_ca ca
synqt_gen_ca foreignca
synqt_gen_entity alpha ca
synqt_gen_entity beta ca
synqt_gen_entity rogue foreignca
synqt_gen_edge_cert impostor ca

chmod 600 ./*.key
synqt_mark_certs .profile
