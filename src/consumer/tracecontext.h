// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#ifndef SYNQT_TRACECONTEXT_H
#define SYNQT_TRACECONTEXT_H

#include <QString>
#include <QVariantMap>

namespace SynQt {

/// Whether a span ended as intended. An enum and not a bool, because `endSpan(span, false)`
/// at a call site says nothing about what false meant.
enum class SpanOutcome {
    Ok,       ///< the work completed
    Failed,   ///< the work was attempted and did not complete
    Refused,  ///< the work was not attempted: a gate said no
};

/// Where one piece of work sits in the story a click tells.
///
/// The identifiers are W3C trace context values, so a `traceparent` header for a
/// third-party collector is a formatting job rather than a mapping one: 32 lower-case hex
/// characters for the trace, 16 for the span, neither all zeroes.
///
/// It lives in the consumer library, away from the tracer, because `Caller` carries one
/// and `Caller` is included nearly everywhere; a header that pulled in the ring buffer and
/// `<atomic>` to say "this call belongs to that trace" would be paid for by every
/// translation unit in the framework. And because the Promise, which the client links
/// without any tracer, has to hold one across a continuation.
struct TraceContext
{
    QString traceId;
    QString spanId;
    QString parentSpanId;
    /// Monotonic microseconds at the moment the span opened; 0 when it opened nowhere.
    qint64 startedUs{0};
    /// What the span is about, and the message of the event that closes it.
    QString name;

    bool isValid() const { return !traceId.isEmpty(); }

    /// The identifiers a peer sent, as a context to continue, or an invalid one.
    ///
    /// A trace identifier that arrives over a link is a calling entity's word, like the
    /// session it travels with, and it is read exactly as far as the shape above allows:
    /// both values must be well-formed W3C identifiers or neither is taken. That is what
    /// keeps a peer from putting a string of its own choosing, of any length, into every
    /// record downstream of it and into every session map forwarded further on.
    static TraceContext fromWire(const QString &traceId, const QString &spanId);

    /// The same, read out of the map a mesh call carries beside its session.
    static TraceContext readFrom(const QVariantMap &session);

    /// Add these identifiers to a map about to travel, and nothing when there are none.
    ///
    /// The pair with \ref readFrom, so the two key names are written once: the reader and
    /// the writer are in different libraries, and a key spelled twice is one that can stop
    /// matching without anything failing to compile.
    void writeTo(QVariantMap &session) const;

    static bool isTraceId(const QString &value);
    static bool isSpanId(const QString &value);
};

} // namespace SynQt

#endif // SYNQT_TRACECONTEXT_H
