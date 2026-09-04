import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from genomesieve.services.ncbi_search import (
    GenomeRecord,
    parse_genome_record,
)
from genomesieve.services.spreadsheet_import import (
    ImportedAccession,
    SpreadsheetImportResult,
)


VALID_REFSEQ = "valid_refseq"
RESOLVED_TO_REFSEQ = "resolved_to_refseq"
GENBANK_ONLY = "genbank_only"
NOT_FOUND = "not_found"
REFSEQ_PAIR_UNAVAILABLE = "refseq_pair_unavailable"


class SpreadsheetValidationError(Exception):
    """Raised when imported accessions cannot be validated."""


@dataclass(frozen=True)
class ValidatedImportedEntry:
    """
    One spreadsheet occurrence after NCBI validation.

    source_entry preserves the original sheet and row.
    """

    source_entry: ImportedAccession

    original_accession: str
    resolved_accession: str | None

    status: str

    record: GenomeRecord | None


@dataclass
class SpreadsheetValidationResult:
    import_result: SpreadsheetImportResult

    entries: list[ValidatedImportedEntry]

    @property
    def ready_entries(self):
        """
        Entries that can be handled by the current RefSeq-only
        GenomeSieve download workflow.
        """

        return [
            entry
            for entry in self.entries
            if entry.status
            in {
                VALID_REFSEQ,
                RESOLVED_TO_REFSEQ,
            }
        ]

    @property
    def resolved_entries(self):
        return [
            entry
            for entry in self.entries
            if entry.status
            == RESOLVED_TO_REFSEQ
        ]

    @property
    def genbank_only_entries(self):
        return [
            entry
            for entry in self.entries
            if entry.status
            == GENBANK_ONLY
        ]

    @property
    def not_found_entries(self):
        return [
            entry
            for entry in self.entries
            if entry.status
            == NOT_FOUND
        ]

    @property
    def unavailable_pair_entries(self):
        return [
            entry
            for entry in self.entries
            if entry.status
            == REFSEQ_PAIR_UNAVAILABLE
        ]

    @property
    def unique_download_records(self):
        """
        Physical downloads are always unique.

        Even if the spreadsheet contains the same accession several
        times, the same GCF file only needs to be downloaded once.
        """

        records = {}
        
        for entry in self.ready_entries:

            if (
                entry.resolved_accession
                and entry.record is not None
            ):
                records.setdefault(
                    entry.resolved_accession,
                    entry.record,
                )

        return list(
            records.values()
        )

    @property
    def duplicate_ready_entries(self):
        return (
            len(self.ready_entries)
            - len(self.unique_download_records)
        )

    def get_dataset_entries(
        self,
        keep_duplicates=True,
    ):
        """
        Return spreadsheet entries according to the user's semantic
        duplicate preference.

        This does NOT change physical download deduplication.
        """

        if keep_duplicates:
            return list(
                self.ready_entries
            )

        unique_entries = []
        seen = set()

        for entry in self.ready_entries:

            accession = (
                entry.resolved_accession
            )

            if accession in seen:
                continue

            seen.add(
                accession
            )

            unique_entries.append(
                entry
            )

        return unique_entries


def validate_imported_accessions(
    import_result: SpreadsheetImportResult,
):
    """
    Validate spreadsheet Assembly Accessions against NCBI.

    GCF accessions are kept when valid.

    GCA accessions are resolved to their paired GCF accession whenever
    NCBI provides a RefSeq pair.

    The validation is performed in batches rather than one request per
    spreadsheet row.
    """

    if not import_result.entries:
        raise SpreadsheetValidationError(
            "There are no Assembly Accessions to validate."
        )

    requested_accessions = sorted(
        {
            entry.accession
            for entry
            in import_result.entries
        }
    )

    # ============================================================
    # FIRST BATCH — ORIGINAL SPREADSHEET ACCESSIONS
    # ============================================================

    original_reports = _query_ncbi_reports(
        requested_accessions
    )

    report_map = _build_report_map(
        original_reports
    )

    # Find GCF pairs referenced by imported GCA records.
    paired_refseq_accessions = set()

    for accession in requested_accessions:

        if not accession.startswith(
            "GCA_"
        ):
            continue

        report = report_map.get(
            accession
        )

        if report is None:
            continue

        paired_accession = (
            _get_paired_accession(
                report
            )
        )

        if (
            paired_accession
            and paired_accession.startswith(
                "GCF_"
            )
        ):
            paired_refseq_accessions.add(
                paired_accession
            )

    # ============================================================
    # SECOND BATCH — GCF PAIRS
    # ============================================================

    missing_paired_accessions = sorted(
        accession
        for accession
        in paired_refseq_accessions
        if accession not in report_map
    )

    if missing_paired_accessions:

        paired_reports = (
            _query_ncbi_reports(
                missing_paired_accessions
            )
        )

        report_map.update(
            _build_report_map(
                paired_reports
            )
        )

    # ============================================================
    # CREATE ONE RESULT PER ORIGINAL SPREADSHEET OCCURRENCE
    # ============================================================

    validated_entries = []

    for source_entry in (
        import_result.entries
    ):

        original_accession = (
            source_entry.accession
        )

        original_report = (
            report_map.get(
                original_accession
            )
        )

        # Syntactically valid, but NCBI returned no assembly.
        if original_report is None:

            validated_entries.append(
                ValidatedImportedEntry(
                    source_entry=source_entry,
                    original_accession=(
                        original_accession
                    ),
                    resolved_accession=None,
                    status=NOT_FOUND,
                    record=None,
                )
            )

            continue

        # ========================================================
        # GCF / REFSEQ
        # ========================================================

        if original_accession.startswith(
            "GCF_"
        ):

            record = parse_genome_record(
                original_report
            )

            if record is None:

                validated_entries.append(
                    ValidatedImportedEntry(
                        source_entry=(
                            source_entry
                        ),
                        original_accession=(
                            original_accession
                        ),
                        resolved_accession=None,
                        status=NOT_FOUND,
                        record=None,
                    )
                )

                continue

            validated_entries.append(
                ValidatedImportedEntry(
                    source_entry=(
                        source_entry
                    ),
                    original_accession=(
                        original_accession
                    ),
                    resolved_accession=(
                        record.accession
                    ),
                    status=VALID_REFSEQ,
                    record=record,
                )
            )

            continue

        # ========================================================
        # GCA / GENBANK
        # ========================================================

        paired_accession = (
            _get_paired_accession(
                original_report
            )
        )

        # No RefSeq equivalent exists.
        if (
            not paired_accession
            or not paired_accession.startswith(
                "GCF_"
            )
        ):

            validated_entries.append(
                ValidatedImportedEntry(
                    source_entry=(
                        source_entry
                    ),
                    original_accession=(
                        original_accession
                    ),
                    resolved_accession=None,
                    status=GENBANK_ONLY,
                    record=None,
                )
            )

            continue

        paired_report = report_map.get(
            paired_accession
        )

        if paired_report is None:

            validated_entries.append(
                ValidatedImportedEntry(
                    source_entry=(
                        source_entry
                    ),
                    original_accession=(
                        original_accession
                    ),
                    resolved_accession=(
                        paired_accession
                    ),
                    status=(
                        REFSEQ_PAIR_UNAVAILABLE
                    ),
                    record=None,
                )
            )

            continue

        paired_record = (
            parse_genome_record(
                paired_report
            )
        )

        if paired_record is None:

            validated_entries.append(
                ValidatedImportedEntry(
                    source_entry=(
                        source_entry
                    ),
                    original_accession=(
                        original_accession
                    ),
                    resolved_accession=(
                        paired_accession
                    ),
                    status=(
                        REFSEQ_PAIR_UNAVAILABLE
                    ),
                    record=None,
                )
            )

            continue

        validated_entries.append(
            ValidatedImportedEntry(
                source_entry=(
                    source_entry
                ),
                original_accession=(
                    original_accession
                ),
                resolved_accession=(
                    paired_record.accession
                ),
                status=(
                    RESOLVED_TO_REFSEQ
                ),
                record=paired_record,
            )
        )

    return SpreadsheetValidationResult(
        import_result=import_result,
        entries=validated_entries,
    )


def _query_ncbi_reports(
    accessions,
):
    """
    Query multiple assembly accessions using NCBI Datasets --inputfile.
    """

    if not accessions:
        return []

    datasets_path = shutil.which(
        "datasets"
    )

    if datasets_path is None:
        raise SpreadsheetValidationError(
            "NCBI Datasets was not found. "
            "Make sure the 'datasets' command is installed "
            "and available in PATH."
        )

    temporary_path = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
        ) as temporary_file:

            temporary_path = (
                temporary_file.name
            )

            for accession in accessions:

                temporary_file.write(
                    accession + "\n"
                )

        command = [
            datasets_path,
            "summary",
            "genome",
            "accession",
            "--inputfile",
            temporary_path,
            "--as-json-lines",
        ]

        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        reports = _parse_json_lines(
            process.stdout
        )

        # NCBI can return some valid records while some input
        # accessions are missing. Missing accessions are handled later
        # as NOT_FOUND.
        #
        # A complete command failure, however, should stop validation.
        if (
            process.returncode != 0
            and not reports
        ):

            message = (
                process.stderr.strip()
                or "NCBI returned an unknown error."
            )

            raise SpreadsheetValidationError(
                "NCBI accession validation failed: "
                f"{message}"
            )

        return reports

    except OSError as exc:

        raise SpreadsheetValidationError(
            f"Could not start NCBI Datasets: {exc}"
        ) from exc

    finally:

        if temporary_path:

            try:
                Path(
                    temporary_path
                ).unlink(
                    missing_ok=True
                )

            except OSError:
                pass


def _parse_json_lines(
    output,
):
    reports = []

    for line in output.splitlines():

        line = line.strip()

        if not line:
            continue

        try:
            data = json.loads(
                line
            )

        except json.JSONDecodeError as exc:

            raise SpreadsheetValidationError(
                "NCBI returned an unexpected response."
            ) from exc

        wrapped_reports = (
            data.get(
                "reports"
            )
        )

        if isinstance(
            wrapped_reports,
            list,
        ):
            reports.extend(
                wrapped_reports
            )

        else:
            reports.append(
                data
            )

    return reports


def _build_report_map(
    reports,
):
    report_map = {}

    for report in reports:

        accession = (
            report.get(
                "accession"
            )
        )

        current_accession = (
            report.get(
                "currentAccession"
            )
            or report.get(
                "current_accession"
            )
        )

        if accession:
            report_map[
                accession
            ] = report

        if current_accession:
            report_map[
                current_accession
            ] = report

    return report_map


def _get_paired_accession(
    report,
):
    paired = (
        report.get(
            "pairedAssembly"
        )
        or report.get(
            "paired_assembly"
        )
        or {}
    )

    return paired.get(
        "accession"
    )