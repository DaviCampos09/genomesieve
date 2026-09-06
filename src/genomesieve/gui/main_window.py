import re
from pathlib import Path
from PySide6.QtGui import QIcon

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
    QFileDialog,
    QHBoxLayout,
    QProgressBar,
    QStackedWidget,
)

from genomesieve.services.reporting import (
    ReportError,
    export_download_report,
    export_search_report,
)

from genomesieve.gui.spreadsheet_import_widget import (
    SpreadsheetImportWidget,
)

from genomesieve.gui.styles import (
    configure_primary_button,
    create_result_metric,
)

from genomesieve.gui.collapsible_section import (
    CollapsibleSection,
)

from genomesieve.gui.search_worker import GenomeSearchWorker
from genomesieve.gui.download_worker import GenomeDownloadWorker

assets_dir = (
    Path(__file__).resolve().parent.parent
    / "assets"
)

csv_icon = QIcon(
    str(assets_dir / "csv.svg")
)

GENBANK_UNSUPPORTED_FILE_FORMATS = {
    "assembly-report": "Assembly Report",
    "assembly-stats": "Assembly Statistics",
    "translated-cds": "Translated CDS FASTA",
}

class CurrentPageStackedWidget(QStackedWidget):
    def sizeHint(self):
        current_widget = self.currentWidget()

        if current_widget is not None:
            return current_widget.sizeHint()

        return super().sizeHint()

    def minimumSizeHint(self):
        current_widget = self.currentWidget()

        if current_widget is not None:
            return current_widget.minimumSizeHint()

        return super().minimumSizeHint()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("GenomeSieve")
        self.resize(1000, 820)
        self.setMinimumSize(750, 550)

        self.current_search_result = None
        self.current_import_validation_result = None
        self.search_worker = None

        self.download_worker = None
        self.download_directory = None

        self.last_download_report_records = []
        self.last_download_destination = None
        self.last_download_formats = []
        self.last_download_source_type = None
        self.last_download_source_name = None

        # ============================================================
        # HEADER
        # ============================================================

        title_label = QLabel("GenomeSieve")

        title_font = title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(
            title_font.pointSize() + 4
        )
        title_label.setFont(title_font)

        description_label = QLabel(
            "Search, filter, and download genome datasets from NCBI."
        )

        description_label.setWordWrap(True)

        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        header_layout.setSpacing(2)

        header_layout.addWidget(
            title_label
        )

        header_layout.addWidget(
            description_label
        )

        # ============================================================
        # GENOME SOURCE
        # ============================================================

        source_group = QGroupBox(
            "Genome source"
        )

        source_layout = QHBoxLayout()

        self.search_by_genus_radio = QRadioButton(
            "Search by genus"
        )

        self.import_spreadsheet_radio = QRadioButton(
            "Import spreadsheet"
        )

        self.search_by_genus_radio.setChecked(
            True
        )

        source_layout.addWidget(
            self.search_by_genus_radio
        )

        source_layout.addWidget(
            self.import_spreadsheet_radio
        )

        source_layout.addStretch()

        source_group.setLayout(
            source_layout
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

        genus_page = QWidget()

        genus_page_layout = QVBoxLayout()

        genus_page_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        genus_page_layout.setSpacing(6)

        genus_page_layout.addWidget(
            genus_label
        )

        genus_page_layout.addWidget(
            self.genus_input
        )

        genus_page_layout.addWidget(
            self.genus_error_label
        )

        genus_page.setLayout(
            genus_page_layout
        )

        self.spreadsheet_import_widget = (
            SpreadsheetImportWidget()
        )

        self.spreadsheet_import_widget.validation_result_changed.connect(
            self.handle_import_validation_result
        )

        self.search_by_genus_radio.toggled.connect(
            self.update_genome_source
        )

        self.import_spreadsheet_radio.toggled.connect(
            self.update_genome_source
        )

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
            "Species filtering"
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

        self.filters_layout = QGridLayout()

        self.filters_layout.addWidget(
            self.assembly_group,
            0,
            0,
        )

        self.filters_layout.addWidget(
            self.format_group,
            0,
            1,
        )

        self.filters_layout.addWidget(
            self.selection_group,
            1,
            0,
        )

        self.filters_layout.addWidget(
            self.unidentified_group,
            1,
            1,
        )

        self.filters_layout.setColumnStretch(
            0,
            1,
        )

        self.filters_layout.setColumnStretch(
            1,
            1,
        )

        # ============================================================
        # SEARCH BUTTON
        # ============================================================

        self.search_button = QPushButton(
            "Search genomes"
        )

        configure_primary_button(
            self.search_button
        )

        self.search_button.clicked.connect(
            self.start_genome_search
        )

        self.search_status_label = QLabel()
        self.search_status_label.hide()

        # ============================================================
        # SEARCH PARAMETERS
        # ============================================================

        self.search_parameters_section = (
            CollapsibleSection(
                "Search parameters"
            )
        )

        self.search_parameters_section.add_widget(
            genus_page
        )

        self.search_parameters_section.add_spacing(
            20
        )

        self.search_parameters_section.add_layout(
            self.filters_layout
        )

        self.search_parameters_section.add_spacing(
            15
        )

        self.search_parameters_section.add_widget(
            self.search_button
        )

        # ============================================================
        # GENUS WORKFLOW PAGE
        # ============================================================

        genus_workflow_page = QWidget()

        genus_workflow_layout = QVBoxLayout(
            genus_workflow_page
        )

        genus_workflow_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        genus_workflow_layout.setSpacing(
            6
        )

        genus_workflow_layout.addWidget(
            self.search_parameters_section
        )

        genus_workflow_layout.addWidget(
            self.search_status_label
        )

        # ============================================================
        # SPREADSHEET WORKFLOW PAGE
        # ============================================================

        spreadsheet_workflow_page = QWidget()

        spreadsheet_workflow_layout = QVBoxLayout(
            spreadsheet_workflow_page
        )

        spreadsheet_workflow_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        spreadsheet_workflow_layout.setSpacing(
            15
        )

        spreadsheet_workflow_layout.addWidget(
            self.spreadsheet_import_widget
        )

        self.import_files_layout = QVBoxLayout()

        self.import_files_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        spreadsheet_workflow_layout.addLayout(
            self.import_files_layout
        )

        # ============================================================
        # GENOME SOURCE STACK
        # ============================================================

        self.source_stack = CurrentPageStackedWidget()

        self.source_stack.addWidget(
            genus_workflow_page
        )

        self.source_stack.addWidget(
            spreadsheet_workflow_page
        )

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

        self.total_assemblies_label = QLabel("0")

        self.identified_species_label = QLabel("0")

        self.unidentified_assemblies_label = QLabel("0")

        results_layout.addWidget(
            create_result_metric(
                self.total_assemblies_label,
                "Assemblies found",
            ),
            0,
            0,
        )

        results_layout.addWidget(
            create_result_metric(
                self.identified_species_label,
                "Identified species",
            ),
            0,
            1,
        )

        results_layout.addWidget(
            create_result_metric(
                self.unidentified_assemblies_label,
                "Unidentified assemblies",
            ),
            0,
            2,
        )

        # ============================================================
        # SECOND ROW
        # ============================================================

        self.selected_assemblies_label = QLabel("0")

        self.selected_species_label = QLabel("0")

        self.reference_genomes_label = QLabel("0")

        results_layout.addWidget(
            create_result_metric(
                self.selected_assemblies_label,
                "Selected assemblies",
            ),
            1,
            0,
        )

        results_layout.addWidget(
            create_result_metric(
                self.selected_species_label,
                "Selected species",
            ),
            1,
            1,
        )

        results_layout.addWidget(
            create_result_metric(
                self.reference_genomes_label,
                "Reference genomes selected",
            ),
            1,
            2,
        )

        # Give all columns equal space.
        results_layout.setColumnStretch(0, 1)
        results_layout.setColumnStretch(1, 1)
        results_layout.setColumnStretch(2, 1)

        results_layout.setHorizontalSpacing(12)
        results_layout.setVerticalSpacing(10)

        # ============================================================
        # SEARCH REPORT EXPORT
        # ============================================================

        self.search_report_button = QPushButton("Export search report")

        self.search_report_button.setIcon(
            QIcon(csv_icon)
        )

        self.search_report_button.setEnabled(
            False
        )

        self.search_report_button.clicked.connect(
            self.export_current_search_report
        )

        search_report_layout = QHBoxLayout()

        search_report_layout.addStretch()

        search_report_layout.addWidget(
            self.search_report_button
        )

        results_layout.addLayout(
            search_report_layout,
            2,
            0,
            1,
            3,
        )

        self.results_group.setLayout(results_layout)
        self.results_group.hide()

        # ============================================================
        # DOWNLOAD
        # ============================================================

        self.download_group = QGroupBox("Download")
        download_layout = QVBoxLayout()

        destination_label = QLabel("Destination folder")

        destination_row = QHBoxLayout()

        self.destination_input = QLineEdit()
        self.destination_input.setReadOnly(True)
        self.destination_input.setPlaceholderText(
            "Select where genome files will be saved"
        )

        self.browse_button = QPushButton("Browse...")

        self.browse_button.clicked.connect(
            self.choose_download_directory
        )

        destination_row.addWidget(
            self.destination_input
        )

        destination_row.addWidget(
            self.browse_button
        )

        self.download_button = QPushButton(
            "Download genomes"
        )

        configure_primary_button(
            self.download_button
        )

        self.download_button.setEnabled(False)

        self.download_button.clicked.connect(
            self.start_genome_download
        )

        self.download_status_label = QLabel()
        self.download_status_label.hide()

        self.download_progress_bar = QProgressBar()

        self.download_progress_bar.setRange(
            0,
            100,
        )

        self.download_progress_bar.setValue(0)

        self.download_progress_bar.setTextVisible(True)

        self.download_progress_bar.hide()

        self.download_progress_details_label = QLabel()

        self.download_progress_details_label.setWordWrap(True)

        self.download_progress_details_label.hide()

        # ============================================================
        # DOWNLOAD REPORT EXPORT
        # ============================================================

        self.download_report_button = QPushButton("Export download report")

        self.download_report_button.setIcon(
            QIcon(csv_icon)
        )

        # There is no valid download report until a download
        # finishes successfully.
        self.download_report_button.setEnabled(
            False
        )

        self.download_report_button.hide()

        self.download_report_button.clicked.connect(
            self.export_current_download_report
        )

        download_report_layout = QHBoxLayout()

        download_report_layout.addStretch()

        download_report_layout.addWidget(
            self.download_report_button
        )

        download_layout.addWidget(destination_label)
        download_layout.addLayout(destination_row)

        download_layout.addSpacing(10)

        download_layout.addWidget(
            self.download_button
        )

        download_layout.addWidget(
            self.download_status_label
        )

        download_layout.addWidget(
            self.download_progress_bar
        )

        download_layout.addWidget(
            self.download_progress_details_label
        )

        download_layout.addLayout(
            download_report_layout
        )

        self.download_group.setLayout(
            download_layout
        )

        # Only shown after a valid genome search.
        self.download_group.hide()

        # ============================================================
        # MAIN CONTENT
        # ============================================================

        content_layout = QVBoxLayout()

        content_layout.addLayout(
            header_layout
        )

        content_layout.addSpacing(12)

        content_layout.addWidget(
            source_group
        )

        content_layout.addWidget(
            self.source_stack
        )

        content_layout.addSpacing(
            10
        )

        content_layout.addWidget(
            self.results_group
        )

        content_layout.addSpacing(10)

        content_layout.addWidget(self.download_group)

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
    
    def update_filter_layout_for_source(
        self,
        import_mode,
    ):
        self.filters_layout.removeWidget(
            self.format_group
        )

        self.import_files_layout.removeWidget(
            self.format_group
        )

        if import_mode:
            self.import_files_layout.addWidget(
                self.format_group
            )

        else:
            self.filters_layout.addWidget(
                self.format_group,
                0,
                1,
            )

        self.format_group.show()

        self.filters_layout.invalidate()
        self.import_files_layout.invalidate()

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

        self.search_report_button.setEnabled(
            True
        )

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

        if result.selected_assemblies > 0:
            self.download_group.show()
            self.update_download_button_state()
        else:
            self.download_group.hide()

        if result.total_assemblies == 0:
            self.search_status_label.setText(
                "No matching assemblies were found."
            )

            self.search_parameters_section.clear_summary()

            self.search_parameters_section.set_expanded(
                True
            )

        else:
            self.search_status_label.setText(
                "Search completed successfully."
            )

            genus = self.genus_input.text().strip()

            self.search_parameters_section.set_summary(
                genus
            )

            self.search_parameters_section.set_expanded(
                False
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

        self.search_report_button.setEnabled(
            False
        )

        self.search_status_label.hide()

        # File format controls are shared with spreadsheet imports.
        # Changing them must not invalidate an existing NCBI
        # validation result.
        if self.import_spreadsheet_radio.isChecked():

            if (
                self.current_import_validation_result
                is not None
                and self.current_import_validation_result
                .unique_download_records
            ):
                self.download_group.show()

                self.update_download_button_state()

            else:
                self.download_group.hide()

            return

        # Genus-search parameters changed, so the previous search
        # is no longer valid.
        self.download_group.hide()

        self.search_parameters_section.clear_summary()

        self.search_parameters_section.set_expanded(
            True
        )

    def set_search_controls_enabled(self, enabled):
        self.genus_input.setEnabled(enabled)

        self.assembly_group.setEnabled(enabled)
        self.format_group.setEnabled(enabled)
        self.selection_group.setEnabled(enabled)
        self.unidentified_group.setEnabled(enabled)

    # ================================================================
    # DOWNLOAD DIRECTORY AND ACTIONS
    # ================================================================

    def choose_download_directory(self):
        initial_directory = (
            self.download_directory
            if self.download_directory
            else str(Path.home())
        )

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select download folder",
            initial_directory,
        )

        if not directory:
            return

        self.download_directory = directory

        self.destination_input.setText(
            directory
        )

        self.update_download_button_state()


    # def update_download_button_state(self):
    #     can_download = (
    #         self.current_search_result is not None
    #         and self.current_search_result.selected_assemblies > 0
    #         and bool(self.download_directory)
    #     )

    #     self.download_button.setEnabled(
    #         can_download
    #     )

    def update_download_button_state(self):
        records = self.get_current_download_records()

        has_destination = bool(
            self.download_directory
        )

        worker = getattr(
            self,
            "download_worker",
            None,
        )

        worker_running = (
            worker is not None
            and worker.isRunning()
        )

        self.download_button.setEnabled(
            bool(records)
            and has_destination
            and not worker_running
        )

    def start_genome_download(self):
       

        if not self.download_directory:
            QMessageBox.warning(
                self,
                "Destination folder required",
                "Select a destination folder before downloading.",
            )
            return

        selected_records = (
            self.get_current_download_records()
        )

        if not selected_records:
            QMessageBox.warning(
                self,
                "No genomes available",
                "There are no validated genomes available for download.",
            )
            return

        file_formats = self.get_selected_formats()

        if not self.confirm_genbank_download_compatibility(
            selected_records,
            file_formats,
        ):
            return

        self.set_search_controls_enabled(False)

        self.search_button.setEnabled(False)
        self.browse_button.setEnabled(False)

        self.download_button.setEnabled(False)
        self.download_button.setText(
            "Downloading..."
        )

        self.download_status_label.setText(
            "Loading NCBI metadata..."
        )

        self.download_status_label.show()


        # Indeterminate mode while ncbi-genome-download checks
        # metadata and determines which files actually need download.
        self.download_progress_bar.setRange(
            0,
            0,
        )

        self.download_progress_bar.show()


        self.download_progress_details_label.setText(
            "Reading and filtering NCBI RefSeq metadata..."
        )

        self.download_progress_details_label.show()

        self.download_report_button.setEnabled(
            False
        )

        self.download_report_button.hide()

        # NOVO: salva exatamente o contexto deste download
        self.active_download_records = list(
            selected_records
        )

        self.active_download_report_records = (
            self.get_current_download_report_records()
        )

        (
            self.active_download_source_type,
            self.active_download_source_name,
        ) = self.get_current_download_source()

        self.active_download_destination = (
            self.download_directory
        )

        self.active_download_formats = list(
            file_formats
        )


        self.download_worker = GenomeDownloadWorker(
            records=selected_records,
            file_formats=file_formats,
            destination=self.download_directory,
        )

        self.download_worker.succeeded.connect(
            self.handle_download_success
        )

        self.download_worker.failed.connect(
            self.handle_download_error
        )

        self.download_worker.progress_changed.connect(
            self.handle_download_progress
        )

        self.download_worker.finished.connect(
            self.finish_download
        )

        self.download_worker.start()

    def confirm_genbank_download_compatibility(
        self,
        records,
        file_formats,
    ):
        genbank_accessions = {
            record.accession
            for record in records
            if record.accession.startswith(
                "GCA_"
            )
        }

        if not genbank_accessions:
            return True

        unsupported_formats = [
            display_name
            for (
                format_key,
                display_name,
            )
            in GENBANK_UNSUPPORTED_FILE_FORMATS.items()
            if format_key in file_formats
        ]

        if not unsupported_formats:
            return True

        supported_formats = [
            file_format
            for file_format in file_formats
            if (
                file_format
                not in GENBANK_UNSUPPORTED_FILE_FORMATS
            )
        ]

        has_refseq_records = any(
            record.accession.startswith(
                "GCF_"
            )
            for record in records
        )

        # There would be nothing at all to download.
        if (
            not supported_formats
            and not has_refseq_records
        ):
            QMessageBox.warning(
                self,
                "Unsupported GenBank file types",
                (
                    "The selected file types are not available "
                    "for GenBank-only assemblies.\n\n"
                    "Select at least one compatible file type "
                    "before starting the download."
                ),
            )

            return False

        unavailable_text = "\n".join(
            f"• {display_name}"
            for display_name
            in unsupported_formats
        )

        message_box = QMessageBox(
            self
        )

        message_box.setIcon(
            QMessageBox.Icon.Warning
        )

        message_box.setWindowTitle(
            "Limited GenBank file availability"
        )

        message_box.setText(
            "Some selected file types are not available "
            "for GenBank-only assemblies."
        )

        message_box.setInformativeText(
            (
                "GenBank-only assemblies: "
                f"{len(genbank_accessions)}\n\n"
                "Unavailable file types:\n"
                f"{unavailable_text}\n\n"
                "If you continue, these file types will still "
                "be downloaded for compatible RefSeq assemblies. "
                "GenBank-only assemblies will receive only the "
                "supported selected file types."
            )
        )

        continue_button = (
            message_box.addButton(
                "Continue download",
                QMessageBox.ButtonRole.AcceptRole,
            )
        )

        cancel_button = (
            message_box.addButton(
                QMessageBox.StandardButton.Cancel
            )
        )

        message_box.setDefaultButton(
            cancel_button
        )

        message_box.exec()

        return (
            message_box.clickedButton()
            is continue_button
        )

    def handle_download_success(self, result):

        self.last_download_report_records = list(
            self.active_download_report_records
        )

        self.last_download_destination = (
            self.active_download_destination
        )

        self.last_download_formats = list(
            self.active_download_formats
        )

        self.last_download_source_type = (
            self.active_download_source_type
        )

        self.last_download_source_name = (
            self.active_download_source_name
        )

        self.download_progress_bar.setRange(
            0,
            100,
        )

        self.download_progress_bar.setValue(
            100
        )

        self.download_status_label.setText(
            "Download completed successfully."
        )

        self.download_report_button.setEnabled(
            True
        )

        self.download_report_button.show()

        if result.completed_files == 0:

            self.download_progress_details_label.setText(
                "All requested files were already present and valid."
            )

        else:

            self.download_progress_details_label.setText(
                f"{result.completed_files} files completed."
            )

        message = (
            "Genome download completed successfully.\n\n"
            f"Assemblies: {result.requested_assemblies}\n"
            f"Files downloaded: {result.completed_files}\n"
            f"Destination:\n{result.destination}"
        )

        QMessageBox.information(
            self,
            "Download completed",
            message,
        )


    def handle_download_error(self, message):

        # Stop indeterminate animation if the error happened
        # during metadata loading.
        self.download_progress_bar.setRange(
            0,
            100,
        )

        self.download_status_label.setText(
            "Download failed."
        )

        QMessageBox.critical(
            self,
            "Genome download failed",
            message,
        )


    def finish_download(self):
        self.set_search_controls_enabled(True)

        self.search_button.setEnabled(True)
        self.browse_button.setEnabled(True)

        self.download_button.setText(
            "Download genomes"
        )

        self.update_download_button_state()

        if self.download_worker is not None:
            self.download_worker.deleteLater()
            self.download_worker = None

    def handle_download_status(self, message):
        self.download_status_label.setText(
            message
        )

    def handle_download_progress(self, progress):

        # ============================================================
        # PHASE 1 — NCBI METADATA
        # ============================================================

        if progress.phase == "metadata":

            self.download_status_label.setText(
                "Loading NCBI metadata..."
            )

            # Indeterminate progress bar.
            self.download_progress_bar.setRange(
                0,
                0,
            )

            self.download_progress_details_label.setText(
                "Reading and filtering NCBI RefSeq metadata..."
            )

            return

        # From this point forward the total amount of work is known.
        self.download_progress_bar.setRange(
            0,
            100,
        )

        self.download_progress_bar.setValue(
            progress.percentage or 0
        )

        # ============================================================
        # PHASE 2 — PREPARING FILES
        # ============================================================

        if progress.phase == "preparing":

            self.download_status_label.setText(
                "Preparing files..."
            )

            details = (
                f"{progress.completed} / "
                f"{progress.total} assemblies prepared"
            )

            if progress.completed == 0:

                details += (
                    "\nEstimating preparation time..."
                )

            elif progress.eta_seconds is not None:

                details += (
                    "\nEstimated preparation time remaining: "
                    f"{self.format_eta(progress.eta_seconds)}"
                )

            if progress.last_item:

                details += (
                    "\nLast prepared: "
                    f"{progress.last_item}"
                )

            self.download_progress_details_label.setText(
                details
            )

            return

        # ============================================================
        # PHASE 3 — DOWNLOADING FILES
        # ============================================================

        if progress.phase == "downloading":

            self.download_status_label.setText(
                "Downloading files..."
            )

            # Everything was already present locally.
            if progress.total == 0:

                self.download_progress_bar.setValue(
                    100
                )

                self.download_progress_details_label.setText(
                    "All requested files are already present and valid."
                )

                return

            details = (
                f"{progress.completed} / "
                f"{progress.total} files completed"
            )

            if progress.completed == 0:

                details += (
                    "\nEstimating download time..."
                )

            elif progress.eta_seconds is not None:

                details += (
                    "\nEstimated download time remaining: "
                    f"{self.format_eta(progress.eta_seconds)}"
                )

            if progress.last_item:

                details += (
                    "\nLast completed: "
                    f"{progress.last_item}"
                )

            self.download_progress_details_label.setText(
                details
            )

    def format_eta(self, seconds):
        seconds = max(
            0,
            round(seconds),
        )

        if seconds < 60:
            return f"{seconds} seconds"

        minutes, seconds = divmod(
            seconds,
            60,
        )

        if minutes < 60:

            if seconds == 0:
                return f"{minutes} min"

            return (
                f"{minutes} min {seconds} s"
            )

        hours, minutes = divmod(
            minutes,
            60,
        )

        if minutes == 0:
            return f"{hours} h"

        return (
            f"{hours} h {minutes} min"
        )
    
    def export_current_search_report(self):

        if self.current_search_result is None:
            return

        genus = self.genus_input.text().strip()

        safe_genus = "".join(
            character
            if character.isalnum()
            else "_"
            for character in genus
        ).strip("_")

        default_filename = (
            f"genomesieve_{safe_genus}_search_report.csv"
        )

        default_path = str(
            Path.home()
            / default_filename
        )

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export search report",
            default_path,
            "CSV files (*.csv)",
        )

        # User cancelled the dialog.
        if not output_path:
            return

        if not output_path.lower().endswith(
            ".csv"
        ):
            output_path += ".csv"

        try:
            report_path = export_search_report(
                result=self.current_search_result,
                output_path=output_path,
                genus=genus,
                assembly_levels=(
                    self.get_selected_assembly_levels()
                ),
                file_formats=(
                    self.get_selected_formats()
                ),
                keep_one_per_species=(
                    self.keep_one_assembly_per_species()
                ),
                remove_unidentified=(
                    self.remove_unidentified_species()
                ),
            )

        except ReportError as exc:

            QMessageBox.warning(
                self,
                "Search report",
                str(exc),
            )

            return

        QMessageBox.information(
            self,
            "Search report",
            (
                "Search report exported successfully.\n\n"
                f"{report_path}"
            ),
        )

    def export_current_download_report(self):

        # There must be a successfully completed download
        # available for reporting.
        if not self.last_download_report_records:
            QMessageBox.warning(
                self,
                "No download report available",
                "Complete a genome download before exporting the report.",
            )
            return

        if not self.last_download_destination:
            QMessageBox.warning(
                self,
                "No download report available",
                "The destination of the last download is unavailable.",
            )
            return

        source_name = (
            self.last_download_source_name
            or "download"
        )

        safe_source_name = "".join(
            character
            if character.isalnum()
            else "_"
            for character in source_name
        ).strip("_")

        default_filename = (
            f"genomesieve_{safe_source_name}_download_report.csv"
        )

        default_path = str(
            Path(
                self.last_download_destination
            )
            / default_filename
        )

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export download report",
            default_path,
            "CSV files (*.csv)",
        )

        if not output_path:
            return

        if not output_path.lower().endswith(
            ".csv"
        ):
            output_path += ".csv"

        try:
            export_download_report(
                records=(
                    self.last_download_report_records
                ),
                destination=(
                    self.last_download_destination
                ),
                source_type=(
                    self.last_download_source_type
                ),
                source_name=(
                    self.last_download_source_name
                ),
                file_formats=(
                    self.last_download_formats
                ),
                output_path=output_path,
            )

        except ReportError as exc:

            QMessageBox.warning(
                self,
                "Download report",
                str(exc),
            )

            return

        QMessageBox.information(
            self,
            "Download report",
            (
                "Download report exported successfully.\n\n"
                f"{output_path}"
            ),
        )

    def update_genome_source(self):

        import_mode = (
            self.import_spreadsheet_radio
            .isChecked()
        )

        self.update_filter_layout_for_source(
            import_mode
        )

        # Switching source mode always discards any previous
        # genus-based search result.
        self.current_search_result = None

        self.results_group.hide()

        self.search_report_button.setEnabled(
            False
        )

        self.search_status_label.hide()

        # If the user returns to genus search, a new search must
        # be performed. Keep the parameters ready for editing.
        self.search_parameters_section.clear_summary()

        self.search_parameters_section.set_expanded(
            True
        )

        if import_mode:

            self.source_stack.setCurrentIndex(
                1
            )

            # These filters belong specifically to genus-based search.
            self.assembly_group.setEnabled(
                False
            )

            self.selection_group.setEnabled(
                False
            )

            self.unidentified_group.setEnabled(
                False
            )

            # File formats are shared by both workflows.
            self.format_group.setEnabled(
                True
            )

            # Preserve a valid spreadsheet import when switching
            # temporarily between source modes.
            if (
                self.current_import_validation_result
                is not None
                and self.current_import_validation_result
                .unique_download_records
            ):
                self.download_group.show()

                self.update_download_button_state()

            else:
                self.download_group.hide()

        else:

            self.source_stack.setCurrentIndex(
                0
            )

            self.assembly_group.setEnabled(
                True
            )

            self.selection_group.setEnabled(
                True
            )

            self.unidentified_group.setEnabled(
                True
            )

            self.format_group.setEnabled(
                True
            )

            # Old genus search results are intentionally not restored.
            self.download_group.hide()

        self.source_stack.updateGeometry()

    def handle_import_validation_result(
        self,
        result,
    ):
        self.current_import_validation_result = (
            result
        )

        if not (
            self.import_spreadsheet_radio
            .isChecked()
        ):
            return

        if (
            result is None
            or not result.unique_download_records
        ):
            self.download_group.hide()

            return

        self.download_group.show()

        self.update_download_button_state()

    def get_current_download_records(self):
        """
        Return the GenomeRecords that must physically be downloaded.

        Spreadsheet imports are always physically deduplicated.
        """

        if (
            self.import_spreadsheet_radio
            .isChecked()
        ):

            result = (
                self.current_import_validation_result
            )

            if result is None:
                return []

            return list(
                result.unique_download_records
            )

        if self.current_search_result is None:
            return []

        return list(
            self.current_search_result
            .selected_records
        )
    
    def get_current_download_report_records(
        self,
    ):
        """
        Return the logical dataset entries for the download report.

        Unlike the physical download list, spreadsheet duplicates may be
        preserved here according to the user's preference.
        """

        if (
            self.import_spreadsheet_radio
            .isChecked()
        ):

            result = (
                self.current_import_validation_result
            )

            if result is None:
                return []

            keep_duplicates = (
                self.spreadsheet_import_widget
                .keep_duplicates_radio
                .isChecked()
            )

            dataset_entries = (
                result.get_dataset_entries(
                    keep_duplicates=(
                        keep_duplicates
                    )
                )
            )

            return [
                entry.record
                for entry in dataset_entries
                if entry.record is not None
            ]

        if self.current_search_result is None:
            return []

        return list(
            self.current_search_result
            .selected_records
        )
    
    def get_current_download_source(
        self,
    ):
        if (
            self.import_spreadsheet_radio
            .isChecked()
        ):

            path = (
                self.spreadsheet_import_widget
                .spreadsheet_path
            )

            if path:
                return (
                    "spreadsheet_import",
                    Path(path).name,
                )

            return (
                "spreadsheet_import",
                "",
            )

        return (
            "genus_search",
            self.genus_input.text().strip(),
        )