import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("GenomeSieve")

        # Initial size large enough for the current interface,
        # while still allowing the user to resize the window.
        self.resize(1000, 720)
        self.setMinimumSize(750, 550)

        # ============================================================
        # HEADER
        # ============================================================

        title_label = QLabel("GenomeSieve")

        description_label = QLabel(
            "Search, filter, and download genome datasets from NCBI."
        )

        # ============================================================
        # GENUS INPUT
        # ============================================================

        genus_label = QLabel("Genus")

        self.genus_input = QLineEdit()
        self.genus_input.setPlaceholderText("e.g., Moellerella")

        self.genus_error_label = QLabel()
        self.genus_error_label.setStyleSheet("color: red;")
        self.genus_error_label.hide()

        self.genus_input.editingFinished.connect(
            self.validate_genus_input
        )

        self.genus_input.textChanged.connect(
            self.clear_genus_error
        )

        # ============================================================
        # ASSEMBLY LEVEL FILTERS
        # ============================================================

        assembly_group = QGroupBox("Assembly level")
        assembly_layout = QVBoxLayout()

        self.complete_checkbox = QCheckBox("Complete Genome")
        self.chromosome_checkbox = QCheckBox("Chromosome")
        self.scaffold_checkbox = QCheckBox("Scaffold")
        self.contig_checkbox = QCheckBox("Contig")

        self.complete_checkbox.setChecked(True)
        self.chromosome_checkbox.setChecked(True)

        assembly_layout.addWidget(self.complete_checkbox)
        assembly_layout.addWidget(self.chromosome_checkbox)
        assembly_layout.addWidget(self.scaffold_checkbox)
        assembly_layout.addWidget(self.contig_checkbox)
        assembly_layout.addStretch()

        assembly_group.setLayout(assembly_layout)

        self.assembly_level_options = {
            "complete": self.complete_checkbox,
            "chromosome": self.chromosome_checkbox,
            "scaffold": self.scaffold_checkbox,
            "contig": self.contig_checkbox,
        }

        # ============================================================
        # FILE FORMAT FILTERS
        # ============================================================

        format_group = QGroupBox("Files")
        format_layout = QGridLayout()

        self.protein_fasta_checkbox = QCheckBox(
            "Protein FASTA (.faa)"
        )

        self.genome_fasta_checkbox = QCheckBox(
            "Genome FASTA (.fna)"
        )

        self.cds_fasta_checkbox = QCheckBox(
            "CDS FASTA (.ffn)"
        )

        self.rna_fasta_checkbox = QCheckBox(
            "RNA FASTA"
        )

        self.gff_checkbox = QCheckBox(
            "GFF"
        )

        self.genbank_checkbox = QCheckBox(
            "GenBank"
        )

        self.assembly_report_checkbox = QCheckBox(
            "Assembly Report"
        )

        self.assembly_stats_checkbox = QCheckBox(
            "Assembly Statistics"
        )

        self.translated_cds_checkbox = QCheckBox(
            "Translated CDS FASTA"
        )

        self.protein_fasta_checkbox.setChecked(True)

        # Two-column organization to use horizontal space better.
        format_layout.addWidget(
            self.protein_fasta_checkbox, 0, 0
        )
        format_layout.addWidget(
            self.genome_fasta_checkbox, 0, 1
        )

        format_layout.addWidget(
            self.cds_fasta_checkbox, 1, 0
        )
        format_layout.addWidget(
            self.rna_fasta_checkbox, 1, 1
        )

        format_layout.addWidget(
            self.gff_checkbox, 2, 0
        )
        format_layout.addWidget(
            self.genbank_checkbox, 2, 1
        )

        format_layout.addWidget(
            self.assembly_report_checkbox, 3, 0
        )
        format_layout.addWidget(
            self.assembly_stats_checkbox, 3, 1
        )

        format_layout.addWidget(
            self.translated_cds_checkbox, 4, 0
        )

        format_group.setLayout(format_layout)

        self.format_options = {
            "protein-fasta": self.protein_fasta_checkbox,
            "fasta": self.genome_fasta_checkbox,
            "cds-fasta": self.cds_fasta_checkbox,
            "rna-fasta": self.rna_fasta_checkbox,
            "gff": self.gff_checkbox,
            "genbank": self.genbank_checkbox,
            "assembly-report": self.assembly_report_checkbox,
            "assembly-stats": self.assembly_stats_checkbox,
            "translated-cds": self.translated_cds_checkbox,
        }

        # ============================================================
        # ASSEMBLY SELECTION STRATEGY
        # ============================================================

        selection_group = QGroupBox("Assemblies per species")
        selection_layout = QVBoxLayout()

        self.keep_all_radio = QRadioButton(
            "Keep all assemblies"
        )

        self.keep_best_radio = QRadioButton(
            "Keep one assembly per species"
        )

        self.keep_best_radio.setChecked(True)

        self.selection_priority_label = QLabel(
            "Selection priority:\n"
            "Reference Genome > Representative Genome > Other\n"
            "Complete Genome > Chromosome > Scaffold > Contig"
        )

        self.selection_priority_label.setWordWrap(True)

        self.keep_all_radio.toggled.connect(
            self.update_selection_priority_visibility
        )

        selection_layout.addWidget(self.keep_all_radio)
        selection_layout.addWidget(self.keep_best_radio)
        selection_layout.addSpacing(10)
        selection_layout.addWidget(self.selection_priority_label)
        selection_layout.addStretch()

        selection_group.setLayout(selection_layout)

        # ============================================================
        # UNIDENTIFIED SPECIES
        # ============================================================

        unidentified_group = QGroupBox("Unidentified species")
        unidentified_layout = QVBoxLayout()

        self.remove_unidentified_checkbox = QCheckBox(
            "Remove unidentified species"
        )

        self.remove_unidentified_checkbox.setChecked(True)

        unidentified_description = QLabel(
            'Removes records such as "Genus sp." or entries without '
            "a known species identification."
        )

        unidentified_description.setWordWrap(True)

        unidentified_layout.addWidget(
            self.remove_unidentified_checkbox
        )

        unidentified_layout.addSpacing(10)

        unidentified_layout.addWidget(
            unidentified_description
        )

        unidentified_layout.addStretch()

        unidentified_group.setLayout(
            unidentified_layout
        )

        # ============================================================
        # FILTER GRID
        # ============================================================

        filters_layout = QGridLayout()

        # First row
        filters_layout.addWidget(
            assembly_group,
            0,
            0,
        )

        filters_layout.addWidget(
            format_group,
            0,
            1,
        )

        # Second row
        filters_layout.addWidget(
            selection_group,
            1,
            0,
        )

        filters_layout.addWidget(
            unidentified_group,
            1,
            1,
        )

        # Give both columns similar available space.
        filters_layout.setColumnStretch(0, 1)
        filters_layout.setColumnStretch(1, 1)

        # ============================================================
        # PAGE CONTENT
        # ============================================================

        content_layout = QVBoxLayout()

        content_layout.addWidget(title_label)
        content_layout.addWidget(description_label)

        content_layout.addSpacing(20)

        content_layout.addWidget(genus_label)
        content_layout.addWidget(self.genus_input)
        content_layout.addWidget(self.genus_error_label)

        content_layout.addSpacing(20)

        content_layout.addLayout(filters_layout)

        content_layout.addStretch()

        content_widget = QWidget()
        content_widget.setLayout(content_layout)

        # ============================================================
        # SCROLL AREA
        # ============================================================

        scroll_area = QScrollArea()

        scroll_area.setWidgetResizable(True)

        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        scroll_area.setWidget(content_widget)

        self.setCentralWidget(scroll_area)

    # ================================================================
    # GENUS VALIDATION
    # ================================================================

    def validate_genus_input(self):
        genus = self.genus_input.text().strip()

        self.genus_input.setText(genus)

        if not genus:
            self.show_genus_error(
                "Please enter a genus name."
            )
            return False

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

    # ================================================================
    # FILTER HELPERS
    # ================================================================

    def get_selected_assembly_levels(self):
        return [
            level
            for level, checkbox in self.assembly_level_options.items()
            if checkbox.isChecked()
        ]

    def get_selected_formats(self):
        return [
            file_format
            for file_format, checkbox in self.format_options.items()
            if checkbox.isChecked()
        ]

    def keep_one_assembly_per_species(self):
        return self.keep_best_radio.isChecked()

    def remove_unidentified_species(self):
        return self.remove_unidentified_checkbox.isChecked()

    def update_selection_priority_visibility(self):
        self.selection_priority_label.setVisible(
            self.keep_best_radio.isChecked()
        )