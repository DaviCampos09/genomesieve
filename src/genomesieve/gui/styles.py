from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


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

def create_result_metric(
    value_label: QLabel,
    description: str,
) -> QWidget:
    value_label.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )

    value_font = value_label.font()
    value_font.setBold(True)

    current_size = value_font.pointSizeF()

    if current_size > 0:
        value_font.setPointSizeF(
            current_size + 5
        )

    value_label.setFont(
        value_font
    )

    description_label = QLabel(
        description
    )

    description_label.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )

    description_label.setWordWrap(
        True
    )

    description_font = (
        description_label.font()
    )

    current_description_size = (
        description_font.pointSizeF()
    )

    if current_description_size > 0:
        description_font.setPointSizeF(
            max(
                current_description_size - 1,
                8,
            )
        )

    description_label.setFont(
        description_font
    )

    metric_layout = QVBoxLayout()

    metric_layout.setContentsMargins(
        4,
        6,
        4,
        6,
    )

    metric_layout.setSpacing(
        2
    )

    metric_layout.addWidget(
        value_label
    )

    metric_layout.addWidget(
        description_label
    )

    metric_widget = QWidget()

    metric_widget.setLayout(
        metric_layout
    )

    return metric_widget