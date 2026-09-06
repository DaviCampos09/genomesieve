from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class CollapsibleSection(QWidget):
    def __init__(
        self,
        title,
        parent=None,
    ):
        super().__init__(parent)

        self._base_title = title
        self._summary = ""

        # ====================================================
        # TOGGLE BUTTON
        # ====================================================

        self.toggle_button = QToolButton()

        self.toggle_button.setText(
            self._base_title
        )

        self.toggle_button.setCheckable(
            True
        )

        self.toggle_button.setChecked(
            True
        )

        self.toggle_button.setArrowType(
            Qt.ArrowType.DownArrow
        )

        self.toggle_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )

        self.toggle_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self.toggle_button.setAutoRaise(
            True
        )

        toggle_font = (
            self.toggle_button.font()
        )

        toggle_font.setBold(
            True
        )

        self.toggle_button.setFont(
            toggle_font
        )

        self.toggle_button.clicked.connect(
            self.set_expanded
        )

        # ====================================================
        # CONTENT
        # ====================================================

        self.content_widget = QWidget()

        self.content_layout = QVBoxLayout(
            self.content_widget
        )

        self.content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.content_layout.setSpacing(
            6
        )

        # ====================================================
        # MAIN LAYOUT
        # ====================================================

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(
            4
        )

        layout.addWidget(
            self.toggle_button
        )

        layout.addWidget(
            self.content_widget
        )

    def add_widget(
        self,
        widget,
    ):
        self.content_layout.addWidget(
            widget
        )

    def add_layout(
        self,
        layout,
    ):
        self.content_layout.addLayout(
            layout
        )

    def add_spacing(
        self,
        spacing,
    ):
        self.content_layout.addSpacing(
            spacing
        )

    def set_expanded(
        self,
        expanded,
    ):
        self.toggle_button.setChecked(
            expanded
        )

        self.toggle_button.setArrowType(
            Qt.ArrowType.DownArrow
            if expanded
            else Qt.ArrowType.RightArrow
        )

        self.content_widget.setVisible(
            expanded
        )

        self.updateGeometry()

    def is_expanded(
        self,
    ):
        return (
            self.toggle_button.isChecked()
        )

    def set_summary(
        self,
        summary,
    ):
        self._summary = (
            summary or ""
        )

        self._update_title()

    def clear_summary(
        self,
    ):
        self._summary = ""

        self._update_title()

    def _update_title(
        self,
    ):
        title = self._base_title

        if self._summary:
            title += (
                f" — {self._summary}"
            )

        self.toggle_button.setText(
            title
        )