// Qt Quick 6.12 migration preview. Values from gc-ui/tokens/gc.tokens.json.
// This opt-in view is not yet the default Linux GUI or a Stable release.
import QtQuick 6.12
import QtQuick.Controls 6.12
import QtQuick.Layouts 6.12
import QtQuick.Dialogs

ApplicationWindow {
    id: win
    objectName: "indexQtWindow"
    title: "GoreeCloud Index — Qt Quick preview"
    // Fit the smallest available logical monitor; never request fullscreen.
    // Sizes come from the same pure policy as GTK, with Qt's 660×488 ideal.
    width: indexBackend.startupWidth; height: indexBackend.startupHeight
    minimumWidth: 390; minimumHeight: 300
    visible: true
    flags: Qt.Window

    readonly property bool dark: indexBackend.dark
    readonly property color canvas: dark ? "#0D121D" : "#F6F7FB"
    readonly property color surface: dark ? "#171D2A" : "#FFFFFF"
    readonly property color tonal: dark ? "#252D3D" : "#EEF0F7"
    readonly property color foreground: dark ? "#F2F4FB" : "#1B2030"
    readonly property color secondary: dark ? "#CED5E5" : "#505B70"
    readonly property color outline: dark ? "#505B70" : "#CED3DF"
    readonly property color accent: dark ? "#8BE7F1" : "#00697A"
    readonly property color onAccent: dark ? "#003A42" : "#FFFFFF"
    readonly property color accentSurface: dark ? "#19525B" : "#C4F2F4"
    readonly property color onAccentSurface: dark ? "#D7FAFF" : "#064D58"
    color: canvas

    readonly property bool compact: width < 520
    property string mode: "all"
    property int selected: 0
    property string chosenExclusionRoot: ""
    readonly property var modes: [
        {label: "All", value: "all"}, {label: "Applications", value: "apps"},
        {label: "Files", value: "files"}, {label: "Actions", value: "actions"}
    ]
    function switchMode(next) {
        mode = next; selected = 0
        indexBackend.refresh(query.text, mode)
        query.forceActiveFocus()
    }
    function activateSelected() { if (indexBackend.results.length) indexBackend.activate(selected) }
    Shortcut { sequences: ["Ctrl+1"]; onActivated: win.switchMode("all") }
    Shortcut { sequences: ["Ctrl+2"]; onActivated: win.switchMode("apps") }
    Shortcut { sequences: ["Ctrl+3"]; onActivated: win.switchMode("files") }
    Shortcut { sequences: ["Ctrl+4"]; onActivated: win.switchMode("actions") }
    Shortcut { sequences: ["Ctrl+L"]; onActivated: query.forceActiveFocus() }
    Connections {
        target: indexBackend
        function onChooseFolder() { picker.open() }
        function onResultsChanged() {
            if (win.selected >= indexBackend.results.length) win.selected = 0
            if (indexBackend.results.length) hits.positionViewAtIndex(win.selected, ListView.Contain)
        }
    }

    Rectangle {
        anchors.fill: parent; anchors.margins: 10
        radius: 26; color: win.surface; border.color: win.outline
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: win.height < 400 ? 12 : 20
            spacing: win.height < 400 ? 8 : 12
            RowLayout {
                Layout.fillWidth: true; spacing: win.compact ? 6 : 10
                Rectangle {
                    width: win.compact ? 34 : 40
                    height: win.compact ? 34 : 40
                    radius: 13; color: win.accentSurface
                    Text { anchors.centerIn: parent; text: "⌕"; color: win.onAccentSurface; font.pixelSize: win.compact ? 24 : 28 }
                }
                ColumnLayout {
                    Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 1
                    Text {
                        Layout.fillWidth: true; Layout.minimumWidth: 0
                        text: "GoreeCloud Index"; color: win.foreground
                        font.pixelSize: win.compact ? 15 : 19
                        font.bold: true; textFormat: Text.PlainText; elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true; Layout.minimumWidth: 0
                        text: win.compact ? "LOCAL · QT PREVIEW" : "LOCAL-FIRST · QT QUICK PREVIEW"
                        font.pixelSize: win.compact ? 8 : 10
                        color: win.secondary; font.letterSpacing: win.compact ? 0.6 : 1.3
                        textFormat: Text.PlainText; elide: Text.ElideRight
                    }
                }
                Button {
                    objectName: "foldersButton"; text: "Folders"
                    implicitHeight: win.compact ? 34 : 40
                    implicitWidth: win.compact ? 69 : 82
                    Accessible.name: "Manage indexing folders"
                    onClicked: foldersDialog.open()
                    background: Rectangle { radius: 12; color: win.tonal; border.color: win.outline }
                    contentItem: Text {
                        text: parent.text; color: win.foreground
                        font.pixelSize: 12; font.bold: true
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                        textFormat: Text.PlainText
                    }
                }
                Button {
                    objectName: "indexAppearanceButton"
                    text: win.compact ? "◐" : "Appearance"
                    implicitHeight: win.compact ? 34 : 40
                    implicitWidth: win.compact ? 34 : 110
                    Accessible.name: "Local appearance preferences"
                    onClicked: themeDialog.open()
                    background: Rectangle { radius: 12; color: win.tonal; border.color: win.outline }
                    contentItem: Text {
                        text: parent.text; color: win.foreground
                        font.pixelSize: 12; font.bold: true
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                        textFormat: Text.PlainText
                    }
                }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: win.height < 400 ? 46 : 54
                radius: 17
                color: win.tonal; border.color: query.activeFocus ? win.accent : win.outline
                border.width: query.activeFocus ? 2 : 1
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 15; anchors.rightMargin: 15
                    Text { text: "⌕"; font.pixelSize: 26; color: win.accent }
                    TextField {
                        id: query; objectName: "indexSearchField"
                        Layout.fillWidth: true; background: null; color: win.foreground
                        font.pixelSize: 17; placeholderText: "Search apps, files or calculate…"
                        placeholderTextColor: win.secondary; focus: true
                        Accessible.name: "Search GoreeCloud Index"
                        Accessible.searchEdit: true
                        Accessible.description: "Search local apps, selected files and safe actions"
                        onTextChanged: { win.selected = 0; indexBackend.refresh(text, win.mode) }
                        Keys.onDownPressed: event => {
                            win.selected = Math.max(0, Math.min(indexBackend.results.length - 1, win.selected + 1))
                            hits.positionViewAtIndex(win.selected, ListView.Contain); event.accepted = true
                        }
                        Keys.onUpPressed: event => {
                            win.selected = Math.max(0, win.selected - 1)
                            hits.positionViewAtIndex(win.selected, ListView.Contain); event.accepted = true
                        }
                        Keys.onReturnPressed: event => { win.activateSelected(); event.accepted = true }
                        Keys.onEscapePressed: event => {
                            if (text.length) text = ""; else win.close(); event.accepted = true
                        }
                    }
                    Text { text: "↵"; color: win.secondary; font.pixelSize: 17 }
                }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 7
                Repeater {
                    model: win.modes
                    delegate: Button {
                        required property var modelData
                        objectName: "indexMode" + modelData.value
                        Layout.fillWidth: true; Layout.minimumWidth: 0
                        Layout.preferredWidth: 1
                        text: win.compact && modelData.value === "apps" ? "Apps" : modelData.label
                        checkable: true; checked: win.mode === modelData.value
                        onClicked: win.switchMode(modelData.value)
                        background: Rectangle {
                            radius: 12; color: parent.checked ? win.accentSurface : win.tonal
                            border.color: parent.checked ? win.accent : win.outline
                        }
                        contentItem: Text {
                            text: parent.text; horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
                            color: parent.checked ? win.onAccentSurface : win.foreground
                            font.pixelSize: win.compact ? 11 : 12
                            font.bold: parent.checked
                            textFormat: Text.PlainText
                        }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: query.text.length ? "RESULTS" : "SUGGESTIONS"
                    font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.5; color: win.secondary
                }
                Item { Layout.fillWidth: true }
                Text { text: indexBackend.results.length + " results"; color: win.secondary; font.pixelSize: 11 }
            }
            ListView {
                id: hits; objectName: "indexResults"
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 6
                model: indexBackend.results; ScrollBar.vertical: ScrollBar {}
                Accessible.role: Accessible.List
                Accessible.name: "Local Index search results"
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    objectName: "indexResultItem" + index
                    width: hits.width; height: 64; radius: 13
                    color: win.selected === index ? win.accentSurface : win.tonal
                    border.color: win.selected === index ? win.accent : "transparent"
                    Accessible.role: Accessible.ListItem
                    Accessible.name: modelData.kind + ": " + modelData.title + ". " + modelData.subtitle
                    Accessible.selectable: true
                    Accessible.selected: win.selected === index
                    Accessible.description: "Activate the selected local result"
                    Accessible.onPressAction: {
                        win.selected = index
                        indexBackend.activate(index)
                    }
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; spacing: 10
                        Rectangle {
                            width: 34; height: 34; radius: 11
                            color: win.selected === index ? win.accent : win.surface
                            Text {
                                anchors.centerIn: parent
                                text: modelData.kind === "app" ? "▦" : modelData.kind === "file" ? "▤"
                                    : modelData.kind === "copy" ? "=" : modelData.kind === "scan" ? "↻" : "+"
                                font.pixelSize: 19
                                color: win.selected === index ? win.onAccent : win.accent
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; Layout.minimumWidth: 0
                            spacing: 3
                            Text {
                                Layout.fillWidth: true; text: modelData.title
                                textFormat: Text.PlainText; elide: Text.ElideRight
                                color: win.selected === index ? win.onAccentSurface : win.foreground
                                font.pixelSize: 14; font.bold: true
                            }
                            Text {
                                Layout.fillWidth: true; text: modelData.subtitle
                                textFormat: Text.PlainText; elide: Text.ElideMiddle
                                color: win.selected === index ? win.onAccentSurface : win.secondary
                                font.pixelSize: 11
                            }
                        }
                        Text {
                            text: modelData.kind.toUpperCase(); font.pixelSize: 10; font.bold: true
                            textFormat: Text.PlainText
                            color: win.selected === index ? win.onAccentSurface : win.secondary
                        }
                    }
                    MouseArea { anchors.fill: parent; onClicked: { win.selected = index; indexBackend.activate(index) } }
                }
            }
            Text {
                visible: !indexBackend.results.length; Layout.fillWidth: true
                text: "No matching local results. Try another search or add a folder."
                textFormat: Text.PlainText; color: win.secondary
                wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                Rectangle { width: 7; height: 7; radius: 4; color: indexBackend.busy ? "#955000" : "#166B4B" }
                Text {
                    objectName: "indexStatusText"
                    Layout.fillWidth: true; text: indexBackend.status; font.pixelSize: 11
                    textFormat: Text.PlainText; elide: Text.ElideRight; color: win.secondary
                    Accessible.role: Accessible.StaticText
                    Accessible.name: indexBackend.status
                }
                BusyIndicator { running: indexBackend.busy; visible: running; Layout.preferredWidth: 22; Layout.preferredHeight: 22 }
            }
        }
    }

    FolderDialog {
        id: picker; title: "Choose a local folder (metadata only)"
        onAccepted: indexBackend.addFolder(selectedFolder.toString())
    }
    FolderDialog {
        id: exclusionPicker
        title: "Exclude a subfolder of the selected indexing root"
        onAccepted: indexBackend.excludeFolder(win.chosenExclusionRoot, selectedFolder.toString())
    }
    Dialog {
        id: foldersDialog; objectName: "indexFoldersDialog"
        modal: true; title: "Folder permissions"
        anchors.centerIn: Overlay.overlay
        width: Math.min(win.width - 24, 610); height: Math.min(win.height - 24, 410)
        standardButtons: Dialog.Close
        background: Rectangle { radius: 20; color: win.surface; border.color: win.outline }
        contentItem: ColumnLayout {
            spacing: 8
            Text { Layout.fillWidth: true; text: "Metadata only by default. Text access requires consent."; color: win.secondary; wrapMode: Text.WordWrap }
            ListView {
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 7
                model: indexBackend.roots; ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    id: rootEntry
                    required property var modelData
                    readonly property string rootPath: modelData.path
                    width: ListView.view.width
                    height: 120 + modelData.exclusions.length * 38
                    radius: 12; color: win.tonal
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 8; spacing: 3
                        Text { Layout.fillWidth: true; text: modelData.path; color: win.foreground; elide: Text.ElideMiddle; textFormat: Text.PlainText; font.pixelSize: 11 }
                        RowLayout {
                            Text {
                                text: !modelData.current ? "REAUTHORIZE"
                                    : modelData.content ? "Text enabled" : "Metadata only"
                                color: win.secondary; font.pixelSize: 11
                            }
                            Item { Layout.fillWidth: true }
                            CloudButton {
                                uiTokens: win
                                text: !modelData.current ? "Reauthorize" : modelData.content ? "Disable text" : "Enable text"
                                enabled: !indexBackend.busy
                                onClicked: {
                                    consentDialog.path = modelData.path
                                    consentDialog.action = !modelData.current ? "reauthorize" : modelData.content ? "disable" : "enable"
                                    consentDialog.open()
                                }
                            }
                            CloudButton {
                                uiTokens: win
                                text: "Remove"; enabled: !indexBackend.busy
                                onClicked: { consentDialog.path = modelData.path; consentDialog.action = "remove"; consentDialog.open() }
                            }
                        }
                        RowLayout {
                            CloudButton {
                                uiTokens: win
                                text: "Exclude subfolder…"
                                enabled: !indexBackend.busy && modelData.current
                                Accessible.name: "Exclude a subfolder inside " + rootEntry.rootPath
                                onClicked: {
                                    win.chosenExclusionRoot = rootEntry.rootPath
                                    exclusionPicker.open()
                                }
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: modelData.exclusions.length + " exclusions"
                                color: win.secondary; font.pixelSize: 10
                                textFormat: Text.PlainText
                            }
                        }
                        Repeater {
                            model: modelData.exclusions
                            delegate: RowLayout {
                                required property string modelData
                                Layout.fillWidth: true
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData; color: win.secondary
                                    textFormat: Text.PlainText; elide: Text.ElideMiddle
                                    font.pixelSize: 10
                                }
                                CloudButton {
                                    uiTokens: win
                                    text: "Allow"
                                    enabled: !indexBackend.busy
                                    Accessible.name: "Remove exclusion for " + modelData
                                    onClicked: indexBackend.unexcludeFolder(rootEntry.rootPath, modelData)
                                }
                            }
                        }
                    }
                }
            }
            RowLayout {
                CloudButton { uiTokens: win; text: "Add folder…"; enabled: !indexBackend.busy; onClicked: picker.open() }
                CloudButton { uiTokens: win; text: "Rescan"; enabled: !indexBackend.busy; onClicked: indexBackend.rescan() }
            }
        }
    }
    Dialog {
        id: consentDialog
        property string path: ""; property string action: ""
        title: "Confirm folder permission"; modal: true
        anchors.centerIn: Overlay.overlay; width: Math.min(win.width - 30, 490)
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentItem: Text {
            width: consentDialog.availableWidth
            text: consentDialog.action === "enable"
                ? "Index bounded local text? Private content could appear in local results. No upload.\n\n" + consentDialog.path
                : consentDialog.action === "disable"
                ? "Remove indexed text now? Keep metadata and original files.\n\n" + consentDialog.path
                : consentDialog.action === "reauthorize"
                ? "Rebind the current directory and clear old indexed data? Text access resets to off.\n\n" + consentDialog.path
                : "Remove indexing permission and cached rows? Original files remain.\n\n" + consentDialog.path
            color: win.foreground; wrapMode: Text.WrapAnywhere; textFormat: Text.PlainText
        }
        onAccepted: {
            if (action === "enable") indexBackend.setContent(path, true)
            else if (action === "disable") indexBackend.setContent(path, false)
            else if (action === "remove") indexBackend.removeFolder(path)
            else if (action === "reauthorize") indexBackend.reauthorizeFolder(path)
        }
    }
    Dialog {
        id: themeDialog; modal: true; title: "Local appearance"
        anchors.centerIn: Overlay.overlay; width: Math.min(win.width - 40, 320)
        standardButtons: Dialog.Close
        contentItem: ColumnLayout {
            Text { text: "Your choice stays on this device."; color: win.secondary; font.pixelSize: 12 }
            Repeater {
                model: ["light", "dark", "auto"]
                delegate: Button {
                    required property string modelData
                    Layout.fillWidth: true
                    text: modelData.charAt(0).toUpperCase() + modelData.slice(1)
                        + (indexBackend.appearance === modelData ? " ✓" : "")
                    onClicked: indexBackend.setAppearance(modelData)
                }
            }
        }
    }
    Component.onCompleted: query.forceActiveFocus()
}
