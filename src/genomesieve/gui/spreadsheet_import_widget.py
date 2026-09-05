from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QRadioButton,
)

from genomesieve.services.spreadsheet_import import (
    SpreadsheetImportError,
    analyze_spreadsheet,
    import_accessions,
)

from genomesieve.gui.spreadsheet_validation_worker import (
    SpreadsheetValidationWorker,
)

from genomesieve.gui.styles import (
    configure_primary_button,
)


class SpreadsheetImportWidget(QWidget):
    """
    Interface responsible only for local spreadsheet analysis.

    No NCBI validation or genome download is performed here.
    """

    import_result_changed = Signal(object)
    validation_result_changed = Signal(object)

    def __init__(self):
        super().__init__()

        self.spreadsheet_path = None
        self.analysis = None
        self.current_import_result = None
        self.current_validation_result = None
        self.validation_worker = None

        self.sheet_controls = {}

        # ============================================================
        # FILE SELECTION
        # ============================================================

        file_group = QGroupBox(
            "Spreadsheet"
        )

        file_layout = QVBoxLayout()

        file_row = QHBoxLayout()

        self.file_input = QLineEdit()
        self.file_input.setReadOnly(True)

        self.file_input.setPlaceholderText(
            "Select an .xlsx spreadsheet"
        )

        self.browse_button = QPushButton(
            "Browse..."
        )

        self.browse_button.clicked.connect(
            self.choose_spreadsheet
        )

        file_row.addWidget(
            self.file_input
        )

        file_row.addWidget(
            self.browse_button
        )

        self.analyze_button = QPushButton(
            "Analyze spreadsheet"
        )

        configure_primary_button(
            self.analyze_button
        )

        self.analyze_button.setEnabled(
            False
        )

        self.analyze_button.clicked.connect(
            self.analyze_selected_spreadsheet
        )

        self.analysis_status_label = QLabel()
        self.analysis_status_label.hide()

        file_layout.addLayout(
            file_row
        )

        file_layout.addWidget(
            self.analyze_button
        )

        file_layout.addWidget(
            self.analysis_status_label
        )

        file_group.setLayout(
            file_layout
        )

        # ============================================================
        # SHEET / COLUMN SELECTION
        # ============================================================

        self.sheets_group = QGroupBox(
            "Assembly accession columns"
        )

        self.sheets_layout = QVBoxLayout()

        self.sheets_group.setLayout(
            self.sheets_layout
        )

        self.sheets_group.hide()

        # ============================================================
        # PREVIEW
        # ============================================================

        self.preview_group = QGroupBox(
            "Import preview"
        )

        preview_layout = QGridLayout()

        preview_layout.addWidget(
            QLabel("Entries found"),
            0,
            0,
        )

        self.entries_label = QLabel("0")

        preview_layout.addWidget(
            self.entries_label,
            1,
            0,
        )

        preview_layout.addWidget(
            QLabel("Unique accessions"),
            0,
            1,
        )

        self.unique_label = QLabel("0")

        preview_layout.addWidget(
            self.unique_label,
            1,
            1,
        )

        preview_layout.addWidget(
            QLabel("Duplicate entries"),
            0,
            2,
        )

        self.duplicates_label = QLabel("0")

        preview_layout.addWidget(
            self.duplicates_label,
            1,
            2,
        )

        preview_layout.addWidget(
            QLabel("Invalid entries"),
            2,
            0,
        )

        self.invalid_label = QLabel("0")

        preview_layout.addWidget(
            self.invalid_label,
            3,
            0,
        )

        preview_layout.addWidget(
            QLabel("Sheets included"),
            2,
            1,
        )

        self.sheets_label = QLabel("0")

        preview_layout.addWidget(
            self.sheets_label,
            3,
            1,
        )

        preview_layout.setColumnStretch(
            0,
            1,
        )

        preview_layout.setColumnStretch(
            1,
            1,
        )

        preview_layout.setColumnStretch(
            2,
            1,
        )

        self.preview_note = QLabel(
            "Local spreadsheet preview only. "
            "Accessions have not yet been validated against NCBI."
        )

        self.preview_note.setWordWrap(
            True
        )

        preview_layout.addWidget(
            self.preview_note,
            4,
            0,
            1,
            3,
        )

        self.preview_group.setLayout(
            preview_layout
        )

        self.preview_group.hide()

        # ============================================================
        # NCBI VALIDATION
        # ============================================================

        self.validation_group = QGroupBox(
            "NCBI validation"
        )

        validation_layout = QVBoxLayout()

        duplicate_label = QLabel(
            "Duplicate handling"
        )

        self.keep_duplicates_radio = (
            QRadioButton(
                "Keep duplicate entries"
            )
        )

        self.remove_duplicates_radio = (
            QRadioButton(
                "Remove duplicate entries"
            )
        )

        # Respect the spreadsheet exactly by default.
        self.keep_duplicates_radio.setChecked(
            True
        )

        self.keep_duplicates_radio.toggled.connect(
            self.update_validation_summary
        )

        self.remove_duplicates_radio.toggled.connect(
            self.update_validation_summary
        )

        duplicate_description = QLabel(
            "Duplicate entries may be preserved in the dataset, "
            "but identical Assembly Accessions will still be "
            "downloaded only once."
        )

        duplicate_description.setWordWrap(
            True
        )

        self.validate_ncbi_button = (
            QPushButton(
                "Validate with NCBI"
            )
        )

        configure_primary_button(
            self.validate_ncbi_button
        )

        self.validate_ncbi_button.setEnabled(
            False
        )

        self.validate_ncbi_button.clicked.connect(
            self.start_ncbi_validation
        )

        self.validation_status_label = QLabel()
        self.validation_status_label.hide()

        validation_layout.addWidget(
            duplicate_label
        )

        validation_layout.addWidget(
            self.keep_duplicates_radio
        )

        validation_layout.addWidget(
            self.remove_duplicates_radio
        )

        validation_layout.addWidget(
            duplicate_description
        )

        validation_layout.addSpacing(
            10
        )

        validation_layout.addWidget(
            self.validate_ncbi_button
        )

        validation_layout.addWidget(
            self.validation_status_label
        )

        self.validation_group.setLayout(
            validation_layout
        )

        self.validation_group.hide()

        # ============================================================
        # VALIDATION RESULTS
        # ============================================================

        self.validation_results_group = QGroupBox(
            "Validated import"
        )

        validation_results_layout = (
            QGridLayout()
        )

        # Row 1
        validation_results_layout.addWidget(
            QLabel("Ready for RefSeq"),
            0,
            0,
        )

        self.ready_label = QLabel("0")

        validation_results_layout.addWidget(
            self.ready_label,
            1,
            0,
        )

        validation_results_layout.addWidget(
            QLabel("GCA resolved to GCF"),
            0,
            1,
        )

        self.resolved_label = QLabel("0")

        validation_results_layout.addWidget(
            self.resolved_label,
            1,
            1,
        )

        validation_results_layout.addWidget(
            QLabel("GenBank-only"),
            0,
            2,
        )

        self.genbank_only_label = QLabel("0")

        validation_results_layout.addWidget(
            self.genbank_only_label,
            1,
            2,
        )

        # Row 2
        validation_results_layout.addWidget(
            QLabel("Not found"),
            2,
            0,
        )

        self.not_found_label = QLabel("0")

        validation_results_layout.addWidget(
            self.not_found_label,
            3,
            0,
        )

        validation_results_layout.addWidget(
            QLabel("Dataset entries"),
            2,
            1,
        )

        self.dataset_entries_label = QLabel("0")

        validation_results_layout.addWidget(
            self.dataset_entries_label,
            3,
            1,
        )

        validation_results_layout.addWidget(
            QLabel("Unique downloads"),
            2,
            2,
        )

        self.unique_downloads_label = QLabel("0")

        validation_results_layout.addWidget(
            self.unique_downloads_label,
            3,
            2,
        )

        validation_results_layout.setColumnStretch(
            0,
            1,
        )

        validation_results_layout.setColumnStretch(
            1,
            1,
        )

        validation_results_layout.setColumnStretch(
            2,
            1,
        )

        self.validation_note = QLabel(
            "Validation completed. Genome files have not been downloaded yet."
        )

        self.validation_note.setWordWrap(
            True
        )

        validation_results_layout.addWidget(
            self.validation_note,
            4,
            0,
            1,
            3,
        )

        self.validation_results_group.setLayout(
            validation_results_layout
        )

        self.validation_results_group.hide()

        # ============================================================
        # ROOT LAYOUT
        # ============================================================

        layout = QVBoxLayout()

        layout.addWidget(
            file_group
        )

        layout.addWidget(
            self.sheets_group
        )

        layout.addWidget(
            self.preview_group
        )

        layout.addWidget(
            self.validation_group
        )

        layout.addWidget(
            self.validation_results_group
        )

        self.setLayout(
            layout
        )

    # ================================================================
    # FILE
    # ================================================================

    def choose_spreadsheet(self):
        file_path, _ = (
            QFileDialog.getOpenFileName(
                self,
                "Select spreadsheet",
                str(Path.home()),
                "Excel workbooks (*.xlsx)",
            )
        )

        if not file_path:
            return

        self.spreadsheet_path = (
            file_path
        )

        self.file_input.setText(
            file_path
        )

        self.analyze_button.setEnabled(
            True
        )

        self.reset_analysis()

    # ================================================================
    # ANALYSIS
    # ================================================================

    def analyze_selected_spreadsheet(
        self,
    ):
        if not self.spreadsheet_path:
            return

        self.analysis_status_label.setText(
            "Analyzing spreadsheet..."
        )

        self.analysis_status_label.show()

        try:
            self.analysis = (
                analyze_spreadsheet(
                    self.spreadsheet_path
                )
            )

        except SpreadsheetImportError as exc:

            self.analysis_status_label.setText(
                "Spreadsheet analysis failed."
            )

            QMessageBox.critical(
                self,
                "Spreadsheet analysis failed",
                str(exc),
            )

            return

        self.build_sheet_controls()

        self.analysis_status_label.setText(
            "Spreadsheet analyzed successfully."
        )

        self.sheets_group.show()

        self.refresh_preview()

    # ================================================================
    # SHEETS
    # ================================================================

    def build_sheet_controls(self):
        self.clear_sheet_controls()

        for sheet in self.analysis.sheets:

            sheet_group = QGroupBox(
                sheet.sheet_name
            )

            layout = QGridLayout()

            column_label = QLabel(
                "Assembly accession column"
            )

            combo = QComboBox()

            # Allows the user to explicitly ignore a worksheet.
            combo.addItem(
                "Do not import this sheet",
                None,
            )

            for column in (
                sheet.available_columns
            ):
                display_name = (
                    f"{column.column_letter} — "
                    f"{column.label}"
                )

                combo.addItem(
                    display_name,
                    column.column_index,
                )

            # Select automatically detected column.
            if (
                sheet.detected_column_index
                is not None
            ):
                detected_combo_index = (
                    combo.findData(
                        sheet.detected_column_index
                    )
                )

                if detected_combo_index >= 0:
                    combo.setCurrentIndex(
                        detected_combo_index
                    )

            detection_label = QLabel()

            if sheet.ambiguous:

                detection_label.setText(
                    "⚠ Multiple possible accession columns "
                    "were detected. Please confirm the column."
                )

            elif (
                sheet.detected_column_index
                is not None
            ):

                detection_label.setText(
                    "✓ Column detected automatically"
                )

            else:

                detection_label.setText(
                    "No accession column was detected. "
                    "Select one manually or skip this sheet."
                )

            detection_label.setWordWrap(
                True
            )

            examples_label = QLabel()

            examples_label.setWordWrap(
                True
            )

            layout.addWidget(
                column_label,
                0,
                0,
            )

            layout.addWidget(
                combo,
                0,
                1,
            )

            layout.addWidget(
                detection_label,
                1,
                0,
                1,
                2,
            )

            layout.addWidget(
                examples_label,
                2,
                0,
                1,
                2,
            )

            sheet_group.setLayout(
                layout
            )

            self.sheets_layout.addWidget(
                sheet_group
            )

            self.sheet_controls[
                sheet.sheet_name
            ] = {
                "combo": combo,
                "examples": examples_label,
            }

            combo.currentIndexChanged.connect(
                lambda _,
                sheet_name=sheet.sheet_name:
                self.handle_column_change(
                    sheet_name
                )
            )

            self.update_column_examples(
                sheet.sheet_name
            )

        self.sheets_layout.addStretch()

    def handle_column_change(
        self,
        sheet_name,
    ):
        self.update_column_examples(
            sheet_name
        )

        self.refresh_preview()

    def update_column_examples(
        self,
        sheet_name,
    ):
        control = (
            self.sheet_controls[
                sheet_name
            ]
        )

        combo = control["combo"]
        examples_label = (
            control["examples"]
        )

        column_index = (
            combo.currentData()
        )

        if column_index is None:

            examples_label.setText(
                "Sheet will not be imported."
            )

            return

        sheet_analysis = next(
            sheet
            for sheet
            in self.analysis.sheets
            if (
                sheet.sheet_name
                == sheet_name
            )
        )

        selected_column = next(
            (
                column
                for column
                in sheet_analysis.available_columns
                if (
                    column.column_index
                    == column_index
                )
            ),
            None,
        )

        if (
            selected_column is None
            or not selected_column.examples
        ):

            examples_label.setText(
                "No example values available."
            )

            return

        examples_label.setText(
            "Examples: "
            + " | ".join(
                selected_column.examples
            )
        )

    # ================================================================
    # PREVIEW
    # ================================================================

    def get_column_selection(self):
        return {
            sheet_name: (
                controls[
                    "combo"
                ].currentData()
            )
            for (
                sheet_name,
                controls,
            )
            in self.sheet_controls.items()
        }

    def refresh_preview(self):
        if (
            self.analysis is None
            or not self.spreadsheet_path
        ):
            return

        column_selection = (
            self.get_column_selection()
        )

        try:
            result = import_accessions(
                self.spreadsheet_path,
                column_selection=(
                    column_selection
                ),
            )

        except SpreadsheetImportError as exc:

            QMessageBox.warning(
                self,
                "Spreadsheet preview",
                str(exc),
            )

            return

        self.current_import_result = (
            result
        )

        # Any change to spreadsheet columns invalidates the
        # previous NCBI validation.
        self.invalidate_validation()

        self.validation_group.setVisible(
            result.total_entries > 0
        )

        self.validate_ncbi_button.setEnabled(
            result.total_entries > 0
        )

        included_sheets = sum(
            1
            for column_index
            in column_selection.values()
            if column_index is not None
        )

        self.entries_label.setText(
            str(
                result.total_entries
            )
        )

        self.unique_label.setText(
            str(
                result.unique_accessions
            )
        )

        self.duplicates_label.setText(
            str(
                result.duplicate_entries
            )
        )

        self.invalid_label.setText(
            str(
                result.total_invalid_entries
            )
        )

        self.sheets_label.setText(
            str(
                included_sheets
            )
        )

        self.preview_group.show()

        self.import_result_changed.emit(
            result
        )

    # ================================================================
    # RESET
    # ================================================================

    def reset_analysis(self):
        self.analysis = None
        self.current_import_result = None

        self.clear_sheet_controls()

        self.sheets_group.hide()
        self.preview_group.hide()

        self.analysis_status_label.hide()

        self.invalidate_validation()

        self.validation_group.hide()

    def clear_sheet_controls(self):
        self.sheet_controls = {}

        while (
            self.sheets_layout.count()
        ):
            item = (
                self.sheets_layout.takeAt(
                    0
                )
            )

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

    def start_ncbi_validation(self):

        if self.current_import_result is None:
            return

        if (
            self.current_import_result
            .total_entries
            == 0
        ):
            return

        self.validate_ncbi_button.setEnabled(
            False
        )

        self.validate_ncbi_button.setText(
            "Validating..."
        )

        self.set_import_controls_enabled(
            False
        )

        self.validation_status_label.setText(
            "Validating Assembly Accessions with NCBI..."
        )

        self.validation_status_label.show()

        self.validation_results_group.hide()

        self.validation_worker = (
            SpreadsheetValidationWorker(
                self.current_import_result
            )
        )

        self.validation_worker.succeeded.connect(
            self.handle_validation_success
        )

        self.validation_worker.failed.connect(
            self.handle_validation_error
        )

        self.validation_worker.finished.connect(
            self.finish_validation
        )

        self.validation_worker.start()

    def handle_validation_success(
        self,
        result,
    ):
        self.current_validation_result = (
            result
        )

        self.validation_result_changed.emit(
            result
        )

        self.validation_status_label.setText(
            "NCBI validation completed successfully."
        )

        self.update_validation_summary()

        self.validation_results_group.show()

    def handle_validation_error(
        self,
        message,
    ):
        self.current_validation_result = None

        self.validation_status_label.setText(
            "NCBI validation failed."
        )

        self.validation_results_group.hide()

        QMessageBox.critical(
            self,
            "NCBI validation failed",
            message,
        )

    def finish_validation(self):

        self.set_import_controls_enabled(
            True
        )

        self.validate_ncbi_button.setText(
            "Validate with NCBI"
        )

        self.validate_ncbi_button.setEnabled(
            (
                self.current_import_result
                is not None
                and self.current_import_result
                .total_entries
                > 0
            )
        )

        if self.validation_worker is not None:

            self.validation_worker.deleteLater()

            self.validation_worker = None

    def update_validation_summary(self):

        if self.current_validation_result is None:
            return

        result = (
            self.current_validation_result
        )

        keep_duplicates = (
            self.keep_duplicates_radio
            .isChecked()
        )

        dataset_entries = (
            result.get_dataset_entries(
                keep_duplicates=keep_duplicates
            )
        )

        self.ready_label.setText(
            str(
                len(result.ready_entries)
            )
        )

        self.resolved_label.setText(
            str(
                len(result.resolved_entries)
            )
        )

        self.genbank_only_label.setText(
            str(
                len(
                    result.genbank_only_entries
                )
            )
        )

        self.not_found_label.setText(
            str(
                len(
                    result.not_found_entries
                )
            )
        )

        self.dataset_entries_label.setText(
            str(
                len(dataset_entries)
            )
        )

        self.unique_downloads_label.setText(
            str(
                len(
                    result.unique_download_records
                )
            )
        )

    def set_import_controls_enabled(
        self,
        enabled,
    ):
        self.browse_button.setEnabled(
            enabled
        )

        self.analyze_button.setEnabled(
            enabled
            and bool(
                self.spreadsheet_path
            )
        )

        for controls in (
            self.sheet_controls.values()
        ):
            controls[
                "combo"
            ].setEnabled(
                enabled
            )

        self.keep_duplicates_radio.setEnabled(
            enabled
        )

        self.remove_duplicates_radio.setEnabled(
            enabled
        )

    def invalidate_validation(self):

        self.current_validation_result = None

        self.validation_results_group.hide()

        self.validation_status_label.hide()

        self.validation_result_changed.emit(
            None
        )