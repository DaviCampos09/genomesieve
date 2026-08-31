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

        layout = QVBoxLayout()
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addSpacing(20)
        layout.addWidget(genus_label)
        layout.addWidget(self.genus_input)
        layout.addStretch()

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)