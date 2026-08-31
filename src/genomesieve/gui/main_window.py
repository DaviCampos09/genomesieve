import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from genomesieve.gui.search_worker import GenomeSearchWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("GenomeSieve")
        self.resize(1000, 820)
        self.setMinimumSize(750, 550)

        self.current_search_result = None
        self.search_worker = None

        # ============================================================
        # HEADER
        # ============================================================

        title_label = QLabel("GenomeSieve")

        description_label = QLabel(
            "Search, filter, and download genome datasets from NCBI."
        )

        # ============================================================
        # GENUS
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

        self.genus_input.textChanged.connect(
            self.invalidate_search_results
        )

        # ============================================================
        # ASSEMBLY LEVEL
        # ============================================================

        self.assembly_group = QGroupBox("Assembly level")
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

        self.assembly_group.setLayout(assembly_layout)

        self.assembly_level_options = {
            "complete": self.complete_checkbox,
            "chromosome": self.chromosome_checkbox,
            "scaffold": self.scaffold_checkbox,
            "contig": self.contig_checkbox,
        }

        # ============================================================
        # FILES
        # ============================================================

        self.format_group = QGroupBox("Files")
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

        self.gff_checkbox = QCheckBox("GFF")
        self.genbank_checkbox = QCheckBox("GenBank")

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

        self.format_group.setLayout(format_layout)

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
        # ASSEMBLY SELECTION
        # ============================================================

        self.selection_group = QGroupBox(
            "Assemblies per species"
        )

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
        selection_layout.addWidget(
            self.selection_priority_label
        )
        selection_layout.addStretch()

        self.selection_group.setLayout(selection_layout)

        # ============================================================
        # UNIDENTIFIED SPECIES
        # ============================================================

        self.unidentified_group = QGroupBox(
            "Unidentified species"
        )

        unidentified_layout = QVBoxLayout()

        self.remove_unidentified_checkbox = QCheckBox(
            "Remove unidentified species"
        )

        self.remove_unidentified_checkbox.setChecked(True)

        unidentified_description = QLabel(
            'Removes records such as "Genus sp." or entries '
            "without a known species identification."
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

        self.unidentified_group.setLayout(
            unidentified_layout
        )

        # ============================================================
        # FILTER CHANGE SIGNALS
        # ============================================================

        for checkbox in self.assembly_level_options.values():
            checkbox.toggled.connect(
                self.invalidate_search_results
            )

        for checkbox in self.format_options.values():
            checkbox.toggled.connect(
                self.invalidate_search_results
            )

        self.keep_all_radio.toggled.connect(
            self.invalidate_search_results
        )

        self.keep_best_radio.toggled.connect(
            self.invalidate_search_results
        )

        self.remove_unidentified_checkbox.toggled.connect(
            self.invalidate_search_results
        )

        # ============================================================
        # FILTER GRID
        # ============================================================

        filters_layout = QGridLayout()

        filters_layout.addWidget(
            self.assembly_group, 0, 0
        )

        filters_layout.addWidget(
            self.format_group, 0, 1
        )

        filters_layout.addWidget(
            self.selection_group, 1, 0
        )

        filters_layout.addWidget(
            self.unidentified_group, 1, 1
        )

        filters_layout.setColumnStretch(0, 1)
        filters_layout.setColumnStretch(1, 1)

        # ============================================================
        # SEARCH BUTTON
        # ============================================================

        self.search_button = QPushButton(
            "Search genomes"
        )

        self.search_button.clicked.connect(
            self.start_genome_search
        )

        self.search_status_label = QLabel()
        self.search_status_label.hide()

        # ============================================================
        # SEARCH RESULTS
        # ============================================================

        self.results_group = QGroupBox(
            "Search results"
        )

        results_layout = QGridLayout()

        # ============================================================
        # FIRST ROW
        # ============================================================

        assemblies_found_title = QLabel("Assemblies found")
        self.total_assemblies_label = QLabel("0")

        identified_species_title = QLabel("Identified species")
        self.identified_species_label = QLabel("0")

        unidentified_title = QLabel("Unidentified assemblies")
        self.unidentified_assemblies_label = QLabel("0")

        results_layout.addWidget(
            assemblies_found_title,
            0,
            0,
            alignment=Qt.AlignCenter,
        )

        results_layout.addWidget(
            identified_species_title,
            0,
            1,
            alignment=Qt.AlignCenter,
        )

        results_layout.addWidget(
            unidentified_title,
            0,
            2,
            alignment=Qt.AlignCenter,
        )

        results_layout.addWidget(
            self.total_assemblies_label,
            1,
            0,
            alignment=Qt.AlignCenter,
        )

        results_layout.addWidget(
            self.identified_species_label,
            1,
            1,
            alignment=Qt.AlignCenter,
        )

        results_layout.addWidget(
            self.unidentified_assemblies_label,
            1,
            2,
            alignment=Qt.AlignCenter,
        )

        # ============================================================
        # SECOND ROW
        # ============================================================

        selected_assemblies_title = QLabel("Selected assemblies")
        self.selected_assemblies_label = QLabel("0")

        selected_species_title = QLabel("Selected species")
        self.selected_species_label = QLabel("0")

        reference_genomes_title = QLabel("Reference genomes selected")
        self.reference_genomes_label = QLabel("0")

        results_layout.addWidget(
            selected_assemblies_title,
            2,
            0,
            alignment=Qt.AlignCenter,
        )

        results_layout.addWidget(
            selected_species_title,
            2,
            1,
            alignment=Qt.AlignCenter,
        )

        results_layout.addWidget(
            reference_genomes_title,
            2,
            2,
            alignment=Qt.AlignCenter,
        )

        results_layout.addWidget(
            self.selected_assemblies_label,
            3,
            0,
            alignment=Qt.AlignCenter,
        )

        results_layout.addWidget(
            self.selected_species_label,
            3,
            1,
            alignment=Qt.AlignCenter,
        )

        results_layout.addWidget(
            self.reference_genomes_label,
            3,
            2,
            alignment=Qt.AlignCenter,
        )

        # Give all columns equal space.
        results_layout.setColumnStretch(0, 1)
        results_layout.setColumnStretch(1, 1)
        results_layout.setColumnStretch(2, 1)

        self.results_group.setLayout(results_layout)
        self.results_group.hide()

        # ============================================================
        # MAIN CONTENT
        # ============================================================

        content_layout = QVBoxLayout()

        content_layout.addWidget(title_label)
        content_layout.addWidget(description_label)

        content_layout.addSpacing(20)

        content_layout.addWidget(genus_label)
        content_layout.addWidget(self.genus_input)
        content_layout.addWidget(
            self.genus_error_label
        )

        content_layout.addSpacing(20)

        content_layout.addLayout(filters_layout)

        content_layout.addSpacing(15)

        content_layout.addWidget(self.search_button)
        content_layout.addWidget(
            self.search_status_label
        )

        content_layout.addSpacing(10)

        content_layout.addWidget(self.results_group)

        content_layout.addStretch()

        content_widget = QWidget()
        content_widget.setLayout(content_layout)

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
                "Enter a valid genus name using letters, "
                "spaces, or hyphens."
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
            for level, checkbox
            in self.assembly_level_options.items()
            if checkbox.isChecked()
        ]

    def get_selected_formats(self):
        return [
            file_format
            for file_format, checkbox
            in self.format_options.items()
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

    # ================================================================
    # SEARCH
    # ================================================================

    def start_genome_search(self):

        if not self.validate_genus_input():
            return

        assembly_levels = (
            self.get_selected_assembly_levels()
        )

        if not assembly_levels:
            QMessageBox.warning(
                self,
                "Assembly level required",
                "Select at least one assembly level.",
            )
            return

        file_formats = self.get_selected_formats()

        if not file_formats:
            QMessageBox.warning(
                self,
                "File format required",
                "Select at least one file format.",
            )
            return

        self.invalidate_search_results()

        self.set_search_controls_enabled(False)

        self.search_button.setEnabled(False)
        self.search_button.setText("Searching...")

        self.search_status_label.setText(
            "Querying NCBI. No genome files are being downloaded..."
        )

        self.search_status_label.show()

        self.search_worker = GenomeSearchWorker(
            genus=self.genus_input.text().strip(),
            assembly_levels=assembly_levels,
            file_formats=file_formats,
            keep_one_per_species=(
                self.keep_one_assembly_per_species()
            ),
            remove_unidentified=(
                self.remove_unidentified_species()
            ),
        )

        self.search_worker.succeeded.connect(
            self.handle_search_success
        )

        self.search_worker.failed.connect(
            self.handle_search_error
        )

        self.search_worker.finished.connect(
            self.finish_search
        )

        self.search_worker.start()

    def handle_search_success(self, result):
        self.current_search_result = result

        self.total_assemblies_label.setText(
            str(result.total_assemblies)
        )

        self.identified_species_label.setText(
            str(result.identified_species)
        )

        self.unidentified_assemblies_label.setText(
            str(result.unidentified_assemblies)
        )

        self.selected_assemblies_label.setText(
            str(result.selected_assemblies)
        )

        self.selected_species_label.setText(
            str(result.selected_species)
        )

        self.reference_genomes_label.setText(
            str(result.selected_reference_genomes)
        )

        self.results_group.show()

        if result.total_assemblies == 0:
            self.search_status_label.setText(
                "No matching assemblies were found."
            )
        else:
            self.search_status_label.setText(
                "Search completed successfully."
            )

    def handle_search_error(self, message):
        self.current_search_result = None
        self.results_group.hide()

        self.search_status_label.setText(
            "Search failed."
        )

        QMessageBox.critical(
            self,
            "Genome search failed",
            message,
        )

    def finish_search(self):
        self.set_search_controls_enabled(True)

        self.search_button.setEnabled(True)
        self.search_button.setText(
            "Search genomes"
        )

        if self.search_worker is not None:
            self.search_worker.deleteLater()
            self.search_worker = None

    def invalidate_search_results(self):
        self.current_search_result = None
        self.results_group.hide()

    def set_search_controls_enabled(self, enabled):
        self.genus_input.setEnabled(enabled)

        self.assembly_group.setEnabled(enabled)
        self.format_group.setEnabled(enabled)
        self.selection_group.setEnabled(enabled)
        self.unidentified_group.setEnabled(enabled)