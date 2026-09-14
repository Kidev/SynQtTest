// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#ifndef SYNQT_OAUTHBACKEND_H
#define SYNQT_OAUTHBACKEND_H

#include "identityconfig.h"

#include <QHash>
#include <QObject>
#include <QString>
#include <QUrl>
#include <QVariantMap>

#include <functional>

QT_BEGIN_NAMESPACE
class QNetworkAccessManager;
class QOAuth2AuthorizationCodeFlow;
class QTimer;
QT_END_NAMESPACE

namespace SynQt {

class JwksVerifier;

/// The secret-bearing OAuth2 / OpenID Connect engine: it holds the client secret, builds
/// the authorization URL (PKCE + state), performs the server-side token exchange, verifies
/// and normalizes the identity (userinfo or a JWKS-verified ID token), and owns the stored
/// access/refresh/ID tokens with their expiry. It also refreshes an access token before it
/// expires, server-side, using the refresh token (see "Session lifecycle" in
/// [Authentication](https://synqt.org/authentication/)).
///
/// This engine is free of any browser I/O: it exposes no cookies and no HTTP
/// routes. The web edge's IdentityProvider drives it for the in-process case; a dedicated
/// auth entity's IdentityService drives the same engine for the provider_entity case, so
/// the secret and the tokens live in exactly one place either way.
class OAuthBackend : public QObject
{
    Q_OBJECT

public:
    explicit OAuthBackend(IdentityConfig config, QObject *parent = nullptr);
    ~OAuthBackend() override;

    /// The authorization step: build the provider's authorize URL and hold a pending login
    /// keyed by the returned state (the PKCE verifier and the OIDC nonce stay here). The
    /// redirectUri is the caller's public callback URL. On failure `error` is set.
    struct BeginResult
    {
        QString state;
        QUrl authorizeUrl;
        QString error;
    };
    /// Two things travel with the state, and they have different jobs:
    ///
    ///  - `binding` is what the caller must present again on the callback, and exchange()
    ///    refuses one that does not. The edge puts the browser's CSRF cookie value here, so
    ///    a state alone is not enough to complete a login.
    ///  - `context` is opaque and is simply handed back on exchange. The edge puts the
    ///    desktop loopback return in it, which it needs to answer the waiting client.
    ///
    /// Both are held here with the state rather than by the caller, which is what lets any
    /// edge process finish a login any other one started (a replicated edge). With a single
    /// edge it changes nothing except where the record lives.
    BeginResult begin(const QString &providerName, const QString &redirectUri,
                      const QString &binding = QString{},
                      const QString &context = QString{});

    /// The token step: exchange the returned authorization code for tokens (client secret +
    /// PKCE verifier), verify and normalize the identity, and store the tokens under a key
    /// (the state, until rekeyed to a stable session id). Consumes the pending state.
    struct ExchangeResult
    {
        QVariantMap identity;
        QString tokenKey;
        QString error;
        /// The `context` begin() was given, back again. It comes back on a failed exchange
        /// too: a desktop login that is refused has to tell the waiting client
        /// so, over the loopback address that is in here, or the app sits on its listener
        /// until the timeout and the visitor reads a refusal as a hang. Empty only when
        /// there was no record to match (unknown or expired state) or the presented binding
        /// did not match it, since neither of those is a login this caller started.
        QString context;
    };
    /// `presentedBinding` is checked against what begin() stored, in constant time, BEFORE
    /// the code is spent: a callback whose binding does not match is somebody else's, and
    /// exchanging first would burn a real authorization code on it. The pending record is
    /// consumed either way, so a callback cannot be replayed against a second process.
    ///
    /// Two forms of the same step. This one waits for the provider and answers when it
    /// has: it is what an HTTP route handler wants, since a route answers when it returns.
    /// A connect point slot may not use it, because a slot that waits holds its entity's
    /// event loop and, worse, lets a mesh link that drops meanwhile tear down the
    /// QtRemoteObjects connection and the Source the slot is still running on. That is
    /// what exchangeAsync is for.
    ExchangeResult exchange(const QString &state, const QString &code,
                            const QString &redirectUri,
                            const QString &presentedBinding = QString{});

    /// The token step as a slot has to run it: nothing waits, and `done` is called with
    /// the result when the provider has answered, which is at once for a refusal that
    /// needs no provider and on a later turn for everything else. The steps a login takes
    /// after the browser came back (the code exchange, then the ID token's key set or the
    /// userinfo profile and the emails fallback) run as each reply arrives.
    using ExchangeCallback = std::function<void(const ExchangeResult &result)>;
    void exchangeAsync(const QString &state, const QString &code, const QString &redirectUri,
                       const QString &presentedBinding, ExchangeCallback done);

    /// Move a stored token entry to a stable key (the session id) once the session exists.
    ///
    /// This is also what marks the entry as claimed: until it happens, the tokens sit
    /// under the state key of a login nobody has bound a session to yet, and
    /// setUnclaimedWindow decides how long that may last.
    void rekeyTokens(const QString &fromKey, const QString &toKey);

    /// How long tokens may sit under a state key before they are let go of.
    ///
    /// An exchange stores what the provider issued and waits for the caller to bind a
    /// session to it; almost always that is the next thing that happens. When it is not,
    /// because the edge that asked went away between the two, the entry used to stay for
    /// the life of the process: an access token and a refresh token for somebody who was
    /// never signed in, and, with the refresh sweep on, a refresh token spent against the
    /// provider once an interval forever. Five minutes by default, which is the window a
    /// login already has. Zero lets go of anything unclaimed at the next sweep.
    void setUnclaimedWindow(int seconds);

    /// The stored tokens for a key (never sent to a browser); empty if none.
    QVariantMap tokens(const QString &key) const;

    void releaseTokens(const QString &key);

    /// How many token entries this engine is holding, under state keys and session ids
    /// alike. A count and nothing else: it exists so a test can ask whether a login that
    /// minted no session left its tokens behind, which is not a question `tokens()` can
    /// answer without the key.
    int heldTokenCount() const;

    /// Refresh every stored access token that is within `marginSeconds` of expiry, using its
    /// refresh token, without involving the browser. Returns how many were refreshed. Called
    /// both directly and by the periodic sweep timer.
    int refreshExpiring(int marginSeconds);

    /// Enable the periodic refresh sweep: every `intervalSeconds` refresh tokens due within
    /// `marginSeconds`. A non-positive interval disables it.
    void setAutoRefresh(int intervalSeconds, int marginSeconds);

    bool providerExists(const QString &name) const;
    bool isDevStub(const QString &name) const;

signals:
    /// Emitted after a stored token entry is refreshed server-side.
    void tokensRefreshed(const QString &key);

private:
    struct Pending
    {
        QOAuth2AuthorizationCodeFlow *flow{nullptr};
        QString providerName;
        QString nonce;
        QString binding;   ///< must be re-presented on the callback; see begin()
        QString context;   ///< opaque, handed back on exchange; see begin()
        qint64 createdMs{0};
    };

    struct TokenEntry
    {
        QString providerName;
        QString accessToken;
        QString refreshToken;
        QString idToken;
        qint64 expiresAtMs{0}; ///< 0 == unknown/never
        /// When this entry was stored, and whether a session has been bound to it. An
        /// unbound entry is a login in flight; see setUnclaimedWindow.
        qint64 storedMs{0};
        bool bound{false};
    };

    /// One exchange in flight; see exchangeAsync. A child of the backend, so a backend
    /// going away takes the exchanges it was running with it, and every callback it holds.
    class ExchangeJob;

    QOAuth2AuthorizationCodeFlow *makeFlow(const IdentityProviderConfig &provider,
                                           const QString &redirectUri);
    /// One bounded GET with a bearer token, answered through `done` with the body, or an
    /// empty body and the error. The provider's profile endpoints are read through this.
    using BodyCallback = std::function<void(const QByteArray &body, const QString &error)>;
    void httpGet(const QUrl &url, const QString &bearer, QObject *context, BodyCallback done);
    QNetworkAccessManager *network();
    bool refreshOne(const QString &key);
    void expirePending();
    /// Drop every entry no session was ever bound to that is past the window. Runs on its
    /// own timer, not the refresh one: refreshing is optional and letting go of a secret
    /// nobody claimed is not.
    void releaseUnclaimed();

    IdentityConfig m_config;
    QNetworkAccessManager *m_network{nullptr};
    JwksVerifier *m_jwks{nullptr};
    QTimer *m_refreshTimer{nullptr};
    QTimer *m_unclaimedTimer{nullptr};
    int m_unclaimedWindowSeconds{300};
    int m_refreshMargin{0};
    bool m_sweeping{false};   ///< a refresh sweep is running; see refreshExpiring()

    QHash<QString, Pending> m_pending;      ///< state -> pending login (verifier + nonce)
    QHash<QString, TokenEntry> m_tokens;    ///< key -> stored tokens
};

} // namespace SynQt

#endif // SYNQT_OAUTHBACKEND_H
