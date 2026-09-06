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
    create_result_metric,
)

from genomesieve.gui.collapsible_section import (
    CollapsibleSection,
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

        self.file_section = CollapsibleSection(
            "Spreadsheet"
        )

        file_layout = QVBoxLayout()

        file_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

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

        self.file_section.add_layout(
            file_layout
        )

        # ============================================================
        # SHEET / COLUMN SELECTION
        # ============================================================

        self.sheets_group = CollapsibleSection(
            "Assembly accession mapping"
        )

        self.sheets_layout = QVBoxLayout()

        self.sheets_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.sheets_layout.setSpacing(
            6
        )

        self.sheets_group.add_layout(
            self.sheets_layout
        )

        self.sheets_group.hide()

        # ============================================================
        # PREVIEW
        # ============================================================

        self.preview_group = CollapsibleSection(
            "Import preview"
        )

        preview_layout = QGridLayout()

        self.entries_label = QLabel("0")
        self.unique_label = QLabel("0")
        self.duplicates_label = QLabel("0")
        self.invalid_label = QLabel("0")
        self.sheets_label = QLabel("0")

        preview_layout.addWidget(
            create_result_metric(
                self.entries_label,
                "Entries found",
            ),
            0,
            0,
        )

        preview_layout.addWidget(
            create_result_metric(
                self.unique_label,
                "Unique accessions",
            ),
            0,
            1,
        )

        preview_layout.addWidget(
            create_result_metric(
                self.duplicates_label,
                "Duplicate entries",
            ),
            0,
            2,
        )

        preview_layout.addWidget(
            create_result_metric(
                self.invalid_label,
                "Invalid entries",
            ),
            1,
            0,
        )

        preview_layout.addWidget(
            create_result_metric(
                self.sheets_label,
                "Sheets included",
            ),
            1,
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

        preview_layout.setHorizontalSpacing(
            12
        )

        preview_layout.setVerticalSpacing(
            10
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
            2,
            0,
            1,
            3,
        )

        self.preview_group.add_layout(
            preview_layout
        )

        self.preview_group.hide()

        # ============================================================
        # NCBI VALIDATION
        # ============================================================

        self.validation_group = CollapsibleSection(
            "NCBI validation"
        )

        validation_layout = QVBoxLayout()

        validation_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        # ------------------------------------------------------------
        # DUPLICATE HANDLING
        # ------------------------------------------------------------

        self.duplicate_options_widget = QWidget()

        duplicate_options_layout = QVBoxLayout(
            self.duplicate_options_widget
        )

        duplicate_options_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        duplicate_options_layout.setSpacing(
            6
        )

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
            "Duplicate rows can be kept in the dataset, "
            "but each Assembly Accession is downloaded only once."
        )

        duplicate_description.setWordWrap(
            True
        )

        duplicate_options_layout.addWidget(
            duplicate_label
        )

        duplicate_options_layout.addWidget(
            self.keep_duplicates_radio
        )

        duplicate_options_layout.addWidget(
            self.remove_duplicates_radio
        )

        duplicate_options_layout.addWidget(
            duplicate_description
        )

        # Message used when the spreadsheet has no duplicate entries.
        self.no_duplicates_label = QLabel(
            "No duplicate entries detected."
        )

        self.no_duplicates_label.hide()

        # ------------------------------------------------------------
        # NCBI VALIDATION BUTTON
        # ------------------------------------------------------------

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

        # ------------------------------------------------------------
        # VALIDATION LAYOUT
        # ------------------------------------------------------------

        validation_layout.addWidget(
            self.duplicate_options_widget
        )

        validation_layout.addWidget(
            self.no_duplicates_label
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

        self.validation_group.add_layout(
            validation_layout
        )

        self.validation_group.hide()

        # ============================================================
        # VALIDATION RESULTS
        # ============================================================

        self.validation_results_group = QGroupBox(
            "Validated import"
        )

        validation_results_layout = QGridLayout()

        self.ready_label = QLabel("0")
        self.resolved_label = QLabel("0")
        self.genbank_only_label = QLabel("0")
        self.not_found_label = QLabel("0")
        self.dataset_entries_label = QLabel("0")
        self.unique_downloads_label = QLabel("0")

        validation_results_layout.addWidget(
            create_result_metric(
                self.ready_label,
                "Ready for RefSeq",
            ),
            0,
            0,
        )

        validation_results_layout.addWidget(
            create_result_metric(
                self.resolved_label,
                "GCA resolved to GCF",
            ),
            0,
            1,
        )

        validation_results_layout.addWidget(
            create_result_metric(
                self.genbank_only_label,
                "GenBank-only",
            ),
            0,
            2,
        )

        validation_results_layout.addWidget(
            create_result_metric(
                self.not_found_label,
                "Not found",
            ),
            1,
            0,
        )

        validation_results_layout.addWidget(
            create_result_metric(
                self.dataset_entries_label,
                "Dataset entries",
            ),
            1,
            1,
        )

        validation_results_layout.addWidget(
            create_result_metric(
                self.unique_downloads_label,
                "Unique downloads",
            ),
            1,
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

        validation_results_layout.setHorizontalSpacing(
            12
        )

        validation_results_layout.setVerticalSpacing(
            10
        )

        self.validation_note = QLabel(
            "Validation completed. Genome files have not been downloaded yet."
        )

        self.validation_note.setWordWrap(
            True
        )

        validation_results_layout.addWidget(
            self.validation_note,
            2,
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
            self.file_section
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

        self.file_section.set_summary(
            Path(file_path).name
        )

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

        sheet_count = len(
            self.analysis.sheets
        )

        sheet_summary = (
            f"{sheet_count} sheet"
            if sheet_count == 1
            else f"{sheet_count} sheets"
        )

        self.sheets_group.set_summary(
            sheet_summary
        )

        self.analysis_status_label.setText(
            "Spreadsheet analyzed successfully."
        )

        self.sheets_group.show()

        self.refresh_preview()

        self.sheets_group.set_expanded(
            True
        )

        self.preview_group.set_expanded(
            True
        )

        self.validation_group.set_expanded(
            True
        )

        self.file_section.set_expanded(
            False
        )

    # ================================================================
    # SHEETS
    # ================================================================

    def build_sheet_controls(self):
        self.clear_sheet_controls()

        instruction_label = QLabel(
            "Confirm the column containing Assembly Accessions "
            "for each sheet."
        )

        instruction_label.setWordWrap(
            True
        )

        self.sheets_layout.addWidget(
            instruction_label
        )

        for sheet in self.analysis.sheets:

            sheet_group = QGroupBox(
                sheet.sheet_name
            )

            layout = QGridLayout()

            layout.setContentsMargins(
                10,
                6,
                10,
                8,
            )

            layout.setHorizontalSpacing(
                12
            )

            layout.setVerticalSpacing(
                4
            )

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

            layout.setColumnStretch(0,0,)

            layout.setColumnStretch(1,1,)

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

        self.preview_group.set_expanded(
            True
        )

        self.validation_group.set_expanded(
            True
        )

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

        entry_count = (
            result.total_entries
        )

        entry_summary = (
            f"{entry_count} entry"
            if entry_count == 1
            else f"{entry_count} entries"
        )

        self.preview_group.set_summary(
            entry_summary
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

        self.update_duplicate_handling_visibility(
            result.duplicate_entries
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

        self.sheets_group.clear_summary()
        self.preview_group.clear_summary()

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

        self.validation_group.set_summary(
            "completed"
        )

        self.update_validation_summary()

        self.validation_results_group.show()

        self.file_section.set_expanded(
            False
        )

        self.sheets_group.set_expanded(
            False
        )

        self.preview_group.set_expanded(
            False
        )

        self.validation_group.set_expanded(
            False
        )

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

        self.validation_group.clear_summary()

        self.validation_results_group.hide()

        self.validation_status_label.hide()

        self.validation_result_changed.emit(
            None
        )

    def update_duplicate_handling_visibility(
        self,
        duplicate_count,
    ):
        has_duplicates = duplicate_count > 0

        self.duplicate_options_widget.setVisible(
            has_duplicates
        )

        self.no_duplicates_label.setVisible(
            not has_duplicates
        )

        if not has_duplicates:
            self.keep_duplicates_radio.setChecked(
                True
            )