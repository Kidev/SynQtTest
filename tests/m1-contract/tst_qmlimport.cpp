// SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
// SPDX-License-Identifier: Apache-2.0

// Registering a contract is what makes `import SynQt` enough.
//
// An entity's QML writes one import line, not two: the SynQt module re-exports QtQuick, so
// a Source can hold a Timer and answer Component.onCompleted without naming QtQuick itself
// (tst_qmlrules proves the engine really does resolve an import that way). That re-export
// used to be installed by a separate call, SynQt::registerModuleImports(), which the
// generated entity main made and nothing else did. Any other host of the same QML - a test
// harness, an embedder, a tool that loads one Source on its own - registered the contract,
// loaded the file, and got a document that would not compile, because the types the file
// leaned on were never in scope. Nothing said so: the edge reports a Source that fails to
// load on a signal, so the browser simply never saw that connect point.
//
// So the re-export rides the registration. This test is the whole reason it does: it
// registers a contract's Sources, the way every host of a Source does, and nothing else.
//
// It runs in its own binary because qmlRegisterModuleImport writes to a process-wide type
// registry. A test that shared a process with anything calling registerModuleImports() -
// tst_qmlrules does - would pass on that call rather than on the one under test.

#include "todo_sourcehelper.h"  // synqtRegisterTodoSources()

#include <QFile>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QTemporaryDir>
#include <QTest>
#include <QUrl>

#include <memory>

class TestQmlImport : public QObject
{
    Q_OBJECT

private slots:
    void initTestCase();
    void registeringSourcesBringsQtQuickWithThem();

private:
    QTemporaryDir m_dir;
};

void TestQmlImport::initTestCase()
{
    QVERIFY(m_dir.isValid());
    // The one call an owner's host makes. Not registerModuleImports(): a host that knew to
    // make that call would not need this test.
    synqtRegisterTodoSources();
}

// A Source shaped like every Source in the repository: rooted at its contract, holding a
// QtQuick child, answering an attached signal handler, with one import line above it.
void TestQmlImport::registeringSourcesBringsQtQuickWithThem()
{
    const QString path{m_dir.filePath(QStringLiteral("Todo.qml"))};
    QFile file{path};
    QVERIFY(file.open(QIODevice::WriteOnly | QIODevice::Text));
    file.write("import SynQt\n"
               "Todo {\n"
               "    Component.onCompleted: count = 1\n"
               "    Timer { interval: 50 }\n"
               "}\n");
    file.close();

    QQmlEngine engine;
    QQmlComponent component{&engine, QUrl::fromLocalFile(path)};
    const std::unique_ptr<QObject> made{component.create()};
    QVERIFY2(made != nullptr, qPrintable(component.errorString()));
    QCOMPARE(made->property("count").toInt(), 1);
}

QTEST_MAIN(TestQmlImport)

#include "tst_qmlimport.moc"
