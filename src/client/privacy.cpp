// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

#include "privacy.h"

#include <QJSEngine>
#include <QQmlEngine>
#include <QSettings>
#include <QUrl>

#include <utility>

namespace SynQt {

namespace {

/// Where a visitor's answer is kept, and the only state this accessor writes anywhere.
///
/// QSettings rather than a cookie, because a record of what a visitor refused is not itself
/// something to ask permission for and putting it in a cookie invites the question. It is
/// per browser profile on the WebAssembly client and per user on a desktop build, which is
/// the same scope the answer has.
constexpr auto AnsweredKey{"SynQt/privacy/answered"};
constexpr auto GrantedKey{"SynQt/privacy/granted"};

} // namespace

/// The object behind `Privacy.hasConsent`, for the reason ScopeCheck exists in session.cpp:
/// the function QML calls has to be a plain closure over one invokable, because a method
/// value lifted off Privacy itself carries the object it came from and calling it as
/// `Privacy.hasConsent(...)` is then a call with a mismatched `this`.
class ConsentCheck : public QObject
{
    Q_OBJECT

public:
    explicit ConsentCheck(const Privacy *privacy, QObject *parent)
        : QObject{parent}
        , m_privacy{privacy}
    {
    }

    Q_INVOKABLE bool held(const QString &category) const
    {
        return m_privacy->hasConsent(category);
    }

private:
    const Privacy *m_privacy;
};

Privacy::Privacy(SynClientConfig config, QJSEngine *engine, QObject *parent)
    : QObject{parent}
    , m_config{std::move(config)}
    , m_engine{engine}
{
    load();
}

QString Privacy::policyUrl() const
{
    return m_config.privacyPolicyUrl;
}

QString Privacy::legalNoticeUrl() const
{
    return m_config.legalNoticeUrl;
}

QString Privacy::contact() const
{
    return m_config.privacyContact;
}

int Privacy::retentionDays() const
{
    return m_config.retentionDays;
}

QStringList Privacy::categories() const
{
    return m_config.cookieCategories;
}

bool Privacy::isConsentRequired() const
{
    return !m_config.cookieCategories.isEmpty();
}

bool Privacy::isConsentAnswered() const
{
    return m_answered;
}

QStringList Privacy::granted() const
{
    return m_granted;
}

QJSValue Privacy::consentCheck() const
{
    // Built on first read rather than in the constructor, because a Privacy is constructed
    // before the engine has a root object and the closure is only ever read from a binding.
    if (!m_checkFunction.isCallable() && m_engine) {
        ConsentCheck *check{new ConsentCheck{this, const_cast<Privacy *>(this)}};
        const QJSValue factory{m_engine->evaluate(QStringLiteral(
            "(function (check) { return function (name) { return check.held(name); }; })"))};
        m_checkFunction = factory.call({m_engine->newQObject(check)});
    }
    return m_checkFunction;
}

bool Privacy::hasConsent(const QString &category) const
{
    // Unanswered is refused, which is what "consent" means: silence is not it, and a page
    // that runs an analytics script while the banner is still up has not been permitted to.
    return m_granted.contains(category);
}

bool Privacy::isErasureOffered() const
{
    return m_config.erasureOffered;
}

void Privacy::accept(const QStringList &categories)
{
    QStringList kept;
    for (const QString &category : categories) {
        // Filtered against what the project declared, so a page cannot grant itself a
        // category nobody wrote down and then read it back as permission.
        if (m_config.cookieCategories.contains(category) && !kept.contains(category)) {
            kept.append(category);
        }
    }
    m_granted = kept;
    m_answered = true;
    store();
    Q_EMIT consentChanged();
}

void Privacy::acceptAll()
{
    accept(m_config.cookieCategories);
}

void Privacy::acceptNecessaryOnly()
{
    accept({});
}

void Privacy::withdrawConsent()
{
    m_granted.clear();
    m_answered = false;
    store();
    Q_EMIT consentChanged();
}

void Privacy::load()
{
    QSettings settings;
    m_answered = settings.value(QLatin1String{AnsweredKey}, false).toBool();
    const QStringList stored{settings.value(QLatin1String{GrantedKey}).toStringList()};
    // Filtered on the way in as well as on the way out. A category the project has since
    // removed is not something this visitor still permits, and a stored answer naming one
    // would otherwise outlive the configuration that offered it.
    for (const QString &category : stored) {
        if (m_config.cookieCategories.contains(category)) {
            m_granted.append(category);
        }
    }
}

void Privacy::store()
{
    QSettings settings;
    settings.setValue(QLatin1String{AnsweredKey}, m_answered);
    settings.setValue(QLatin1String{GrantedKey}, m_granted);
}

void registerPrivacyTypes()
{
    // Absolute URLs, which is what this overload requires. The three files are in this
    // library's own resource, so they are there whether or not the app ships any QML of its
    // own with the same names.
    qmlRegisterType(QUrl{QStringLiteral("qrc:/qt/qml/SynQt/privacy/LegalFooter.qml")},
                    "SynQt", 1, 0, "LegalFooter");
    qmlRegisterType(QUrl{QStringLiteral("qrc:/qt/qml/SynQt/privacy/CookieConsent.qml")},
                    "SynQt", 1, 0, "CookieConsent");
    qmlRegisterType(QUrl{QStringLiteral("qrc:/qt/qml/SynQt/privacy/DataErasureRequest.qml")},
                    "SynQt", 1, 0, "DataErasureRequest");
}

} // namespace SynQt

#include "privacy.moc"
