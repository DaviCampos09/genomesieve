from PySide6.QtCore import QThread, Signal

from genomesieve.services.ncbi_download import (
    GenomeDownloadError,
    download_genomes,
)


class GenomeDownloadWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    progress_changed = Signal(object)

    def __init__(
        self,
        records,
        file_formats,
        destination,
    ):
        super().__init__()

        self.records = records
        self.file_formats = file_formats
        self.destination = destination

    def run(self):
        try:
            result = download_genomes(
                records=self.records,
                file_formats=self.file_formats,
                destination=self.destination,
                progress_callback=self.progress_changed.emit,
            )

            self.succeeded.emit(result)

        except GenomeDownloadError as exc:
            self.failed.emit(str(exc))

        except Exception as exc:
            self.failed.emit(
                f"An unexpected error occurred: {exc}"
            )