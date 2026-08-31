from PySide6.QtCore import QThread, Signal

from genomesieve.services.ncbi_search import (
    GenomeSearchError,
    search_genomes,
)


class GenomeSearchWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        genus,
        assembly_levels,
        file_formats,
        keep_one_per_species,
        remove_unidentified,
    ):
        super().__init__()

        self.genus = genus
        self.assembly_levels = assembly_levels
        self.file_formats = file_formats
        self.keep_one_per_species = keep_one_per_species
        self.remove_unidentified = remove_unidentified

    def run(self):
        try:
            result = search_genomes(
                genus=self.genus,
                assembly_levels=self.assembly_levels,
                file_formats=self.file_formats,
                keep_one_per_species=self.keep_one_per_species,
                remove_unidentified=self.remove_unidentified,
            )

            self.succeeded.emit(result)

        except GenomeSearchError as exc:
            self.failed.emit(str(exc))

        except Exception as exc:
            self.failed.emit(
                f"An unexpected error occurred: {exc}"
            )