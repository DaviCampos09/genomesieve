import re

from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("GenomeSieve")
        self.setMinimumSize(600, 300)

        title_label = QLabel("GenomeSieve")

        description_label = QLabel(
            "Search, filter, and download genome datasets from NCBI."
        )

        genus_label = QLabel("Genus")

        self.genus_input = QLineEdit()
        self.genus_input.setPlaceholderText("e.g., Moellerella")

        self.genus_error_label = QLabel()
        self.genus_error_label.setStyleSheet("color: red;")
        self.genus_error_label.hide()

        # Validate when the user finishes editing the field.
        self.genus_input.editingFinished.connect(
            self.validate_genus_input
        )

        # Remove the error message as soon as the user starts correcting input.
        self.genus_input.textChanged.connect(
            self.clear_genus_error
        )

        layout = QVBoxLayout()
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addSpacing(20)
        layout.addWidget(genus_label)
        layout.addWidget(self.genus_input)
        layout.addWidget(self.genus_error_label)
        layout.addStretch()

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

    def validate_genus_input(self):
        genus = self.genus_input.text().strip()

        # Remove unnecessary spaces at the beginning and end.
        self.genus_input.setText(genus)

        if not genus:
            self.show_genus_error("Please enter a genus name.")
            return False

        # Accepts letters and optional words separated by spaces or hyphens.
        # Examples:
        # Moellerella
        # Candidatus Something
        # Example-Genus
        pattern = r"^[A-Za-z]+(?:[ -][A-Za-z]+)*$"

        if not re.fullmatch(pattern, genus):
            self.show_genus_error(
                "Enter a valid genus name using letters, spaces, or hyphens."
            )
            return False

        self.genus_error_label.hide()
        return True

    def show_genus_error(self, message):
        self.genus_error_label.setText(message)
        self.genus_error_label.show()

    def clear_genus_error(self):
        self.genus_error_label.hide()