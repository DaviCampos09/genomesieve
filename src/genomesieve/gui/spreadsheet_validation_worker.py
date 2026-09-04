from PySide6.QtCore import (
    QThread,
    Signal,
)

from genomesieve.services.spreadsheet_validation import (
    SpreadsheetValidationError,
    validate_imported_accessions,
)


class SpreadsheetValidationWorker(
    QThread
):
    succeeded = Signal(
        object
    )

    failed = Signal(
        str
    )

    def __init__(
        self,
        import_result,
    ):
        super().__init__()

        self.import_result = (
            import_result
        )

    def run(self):

        try:

            result = (
                validate_imported_accessions(
                    self.import_result
                )
            )

            self.succeeded.emit(
                result
            )

        except SpreadsheetValidationError as exc:

            self.failed.emit(
                str(exc)
            )

        except Exception as exc:

            self.failed.emit(
                "An unexpected error occurred: "
                f"{exc}"
            )