// GoreeCloud UI alpha semantic Cloud Surface action for Qt Quick dialogs.
// Use supplied window role colors; never impose one global hue.
import QtQuick 6.12
import QtQuick.Controls 6.12

Button {
    id: control
    property var uiTokens: null

    implicitHeight: 35
    implicitWidth: Math.max(76, label.implicitWidth + 24)
    background: Rectangle {
        radius: 11
        color: control.uiTokens
            ? (control.down ? control.uiTokens.accentSurface : control.uiTokens.surface)
            : (control.down ? "#C4F2F4" : "#FFFFFF")
        border.color: control.activeFocus && control.uiTokens
            ? control.uiTokens.accent
            : (control.uiTokens ? control.uiTokens.outline : "#CED3DF")
        border.width: control.activeFocus ? 2 : 1
        opacity: control.enabled ? 1 : 0.48
    }
    contentItem: Text {
        id: label
        text: control.text
        textFormat: Text.PlainText
        font.pixelSize: 11
        font.bold: control.activeFocus
        color: control.uiTokens ? control.uiTokens.foreground : "#1B2030"
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
        opacity: control.enabled ? 1 : 0.48
    }
}
