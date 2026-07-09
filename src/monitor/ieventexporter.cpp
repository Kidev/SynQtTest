// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#include "ieventexporter.h"

namespace SynQt {

// Out of line so the vtable has one home, rather than one per translation unit that
// includes the header.
IEventExporter::~IEventExporter() = default;

} // namespace SynQt
