from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QPushButton


def configure_primary_button(
    button: QPushButton,
) -> None:
    font = button.font()
    font.setBold(True)
    button.setFont(font)

    button.setMinimumHeight(
        button.sizeHint().height() + 8
    )

    palette = button.palette()

    accent_color = palette.color(
        QPalette.ColorRole.Highlight
    )

    accent_text_color = palette.color(
        QPalette.ColorRole.HighlightedText
    )

    disabled_background = palette.color(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Button,
    )

    disabled_text = palette.color(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
    )

    button.setStyleSheet(
        f"""
        QPushButton {{
            background-color: {accent_color.name()};
            color: {accent_text_color.name()};
            border: 1px solid {accent_color.darker(115).name()};
            border-radius: 4px;
            padding: 6px 12px;
        }}

        QPushButton:hover {{
            background-color: {accent_color.lighter(108).name()};
        }}

        QPushButton:pressed {{
            background-color: {accent_color.darker(108).name()};
        }}

        QPushButton:disabled {{
            background-color: {disabled_background.name()};
            color: {disabled_text.name()};
            border-color: {disabled_background.darker(110).name()};
        }}
        """
    )