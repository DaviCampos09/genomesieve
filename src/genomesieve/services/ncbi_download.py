import shutil
import subprocess
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ncbi_genome_download import NgdConfig
from ncbi_genome_download.core import (
    create_downloadjob,
    select_candidates,
    worker,
)

from genomesieve.services.ncbi_search import GenomeRecord

GENBANK_DATASETS_FORMATS = {
    "protein-fasta": {
        "include": "protein",
        "patterns": (
            "protein.faa",
        ),
    },
    "fasta": {
        "include": "genome",
        "patterns": (
            "*_genomic.fna",
        ),
    },
    "cds-fasta": {
        "include": "cds",
        "patterns": (
            "cds_from_genomic.fna",
            "cds.fna",
        ),
    },
    "rna-fasta": {
        "include": "rna",
        "patterns": (
            "rna.fna",
        ),
    },
    "gff": {
        "include": "gff3",
        "patterns": (
            "genomic.gff",
        ),
    },
    "genbank": {
        "include": "gbff",
        "patterns": (
            "genomic.gbff",
        ),
    },
}


class GenomeDownloadError(Exception):
    """Raised when genome files cannot be downloaded."""


@dataclass(frozen=True)
class DownloadProgress:
    """
    Represents progress in one of the GenomeSieve download phases.

    phase:
        "metadata"
        "preparing"
        "downloading"
    """

    phase: str

    completed: int
    total: int

    percentage: int | None
    eta_seconds: float | None

    last_item: str | None = None


@dataclass
class GenomeDownloadResult:
    destination: Path
    requested_assemblies: int
    requested_formats: list[str]
    completed_files: int


def download_genomes(
    records: list[GenomeRecord],
    file_formats: list[str],
    destination: str,
    progress_callback: Callable[[DownloadProgress], None] | None = None,
) -> GenomeDownloadResult:
    """
    Download exactly the assemblies selected by GenomeSieve.

    The process is divided into three observable phases:

    1. metadata
       Load and filter NCBI assembly metadata.

    2. preparing
       Check each assembly, retrieve checksum information and determine
       which files actually need to be downloaded.

    3. downloading
       Download and checksum-validate the required files.
    """

    if not records:
        raise GenomeDownloadError(
            "There are no selected assemblies to download."
        )

    if not file_formats:
        raise GenomeDownloadError(
            "Select at least one file format."
        )

    destination_path = Path(destination)

    try:
        destination_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    except OSError as exc:
        raise GenomeDownloadError(
            f"Could not create the destination folder: {exc}"
        ) from exc

    accessions = [
        record.accession
        for record in records
    ]

    # ============================================================
    # PHASE 1 — LOADING NCBI METADATA
    # ============================================================

    _emit_progress(
        progress_callback,
        phase="metadata",
        completed=0,
        total=0,
        percentage=None,
        eta_seconds=None,
    )

    try:
        config = NgdConfig.from_kwargs(
            groups=["bacteria"],
            section="refseq",
            file_formats=file_formats,
            assembly_accessions=accessions,
            output=str(destination_path),
            flat_output=True,

            # GenomeSieve manages parallel file downloads itself so
            # progress can be tracked reliably.
            parallel=1,

            use_cache=True,
        )

        candidates = select_candidates(config)

    except Exception as exc:
        raise GenomeDownloadError(
            f"Could not load NCBI genome metadata: {exc}"
        ) from exc

    if not candidates:
        raise GenomeDownloadError(
            "No matching RefSeq assemblies were found for download."
        )

    # ============================================================
    # PHASE 2 — PREPARING FILES
    # ============================================================

    total_assemblies = len(candidates)

    _emit_progress(
        progress_callback,
        phase="preparing",
        completed=0,
        total=total_assemblies,
        percentage=0,
        eta_seconds=None,
    )

    preparation_start = time.monotonic()

    download_jobs = []

    for index, (entry, group) in enumerate(
        candidates,
        start=1,
    ):
        accession = entry.get(
            "assembly_accession",
            "Unknown accession",
        )

        try:
            jobs = create_downloadjob(
                entry,
                group,
                config,
            )

            download_jobs.extend(jobs)

        except Exception as exc:
            raise GenomeDownloadError(
                f"Could not prepare files for {accession}: {exc}"
            ) from exc

        elapsed = (
            time.monotonic()
            - preparation_start
        )

        remaining = (
            total_assemblies
            - index
        )

        if index > 0:
            average_time = (
                elapsed
                / index
            )

            eta_seconds = (
                average_time
                * remaining
            )

        else:
            eta_seconds = None

        percentage = round(
            index
            / total_assemblies
            * 100
        )

        _emit_progress(
            progress_callback,
            phase="preparing",
            completed=index,
            total=total_assemblies,
            percentage=percentage,
            eta_seconds=eta_seconds,
            last_item=accession,
        )

    # ============================================================
    # NO FILES NEED DOWNLOADING
    # ============================================================

    total_files = len(download_jobs)

    if total_files == 0:

        _emit_progress(
            progress_callback,
            phase="downloading",
            completed=0,
            total=0,
            percentage=100,
            eta_seconds=0,
        )

        return GenomeDownloadResult(
            destination=destination_path,
            requested_assemblies=len(records),
            requested_formats=file_formats,
            completed_files=0,
        )

    # ============================================================
    # PHASE 3 — DOWNLOADING FILES
    # ============================================================

    _emit_progress(
        progress_callback,
        phase="downloading",
        completed=0,
        total=total_files,
        percentage=0,
        eta_seconds=None,
    )

    download_start = time.monotonic()

    completed_files = 0

    # Conservative default.
    max_workers = min(
        4,
        total_files,
    )

    try:
        with ThreadPoolExecutor(
            max_workers=max_workers
        ) as executor:

            future_to_job = {
                executor.submit(worker, job): job
                for job in download_jobs
            }

            for future in as_completed(
                future_to_job
            ):
                job = future_to_job[future]

                result = future.result()

                if result is False:
                    raise GenomeDownloadError(
                        "A downloaded file failed checksum validation: "
                        f"{Path(job.local_file).name}"
                    )

                completed_files += 1

                elapsed = (
                    time.monotonic()
                    - download_start
                )

                remaining_files = (
                    total_files
                    - completed_files
                )

                if completed_files > 0:

                    average_time = (
                        elapsed
                        / completed_files
                    )

                    eta_seconds = (
                        average_time
                        * remaining_files
                    )

                else:
                    eta_seconds = None

                percentage = round(
                    completed_files
                    / total_files
                    * 100
                )

                _emit_progress(
                    progress_callback,
                    phase="downloading",
                    completed=completed_files,
                    total=total_files,
                    percentage=percentage,
                    eta_seconds=eta_seconds,
                    last_item=Path(
                        job.local_file
                    ).name,
                )

    except GenomeDownloadError:
        raise

    except Exception as exc:
        raise GenomeDownloadError(
            f"Genome download failed: {exc}"
        ) from exc

    return GenomeDownloadResult(
        destination=destination_path,
        requested_assemblies=len(records),
        requested_formats=file_formats,
        completed_files=completed_files,
    )

def _download_genbank_with_datasets(
    records,
    file_formats,
    destination_path,
):
    """
    Download GenBank-only assemblies through NCBI Datasets.

    The NCBI Datasets package is downloaded and extracted in a
    temporary directory. Only the files requested by the user are
    copied to the final GenomeSieve destination.
    """

    genbank_records = [
        record
        for record in records
        if record.accession.startswith(
            "GCA_"
        )
    ]

    if not genbank_records:
        return []

    supported_formats = [
        file_format
        for file_format in file_formats
        if file_format
        in GENBANK_DATASETS_FORMATS
    ]

    if not supported_formats:
        return []

    datasets_path = shutil.which(
        "datasets"
    )

    if datasets_path is None:
        raise GenomeDownloadError(
            "NCBI Datasets was not found. "
            "Make sure the 'datasets' command is installed "
            "and available in PATH."
        )

    accessions = list(
        dict.fromkeys(
            record.accession
            for record
            in genbank_records
        )
    )

    include_formats = list(
        dict.fromkeys(
            GENBANK_DATASETS_FORMATS[
                file_format
            ]["include"]
            for file_format
            in supported_formats
        )
    )

    copied_files = []

    with tempfile.TemporaryDirectory(
        prefix="genomesieve_genbank_"
    ) as temporary_directory:

        temporary_path = Path(
            temporary_directory
        )

        accessions_file = (
            temporary_path
            / "accessions.txt"
        )

        package_path = (
            temporary_path
            / "genbank_dataset.zip"
        )

        extracted_path = (
            temporary_path
            / "extracted"
        )

        accessions_file.write_text(
            "\n".join(
                accessions
            )
            + "\n",
            encoding="utf-8",
        )

        command = [
            datasets_path,
            "download",
            "genome",
            "accession",
            "--inputfile",
            str(
                accessions_file
            ),
            "--assembly-version",
            "all",
            "--include",
            ",".join(
                include_formats
            ),
            "--filename",
            str(
                package_path
            ),
            "--no-progressbar",
        ]

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )

        except OSError as exc:
            raise GenomeDownloadError(
                "Could not start NCBI Datasets: "
                f"{exc}"
            ) from exc

        if process.returncode != 0:

            error_message = (
                process.stderr.strip()
                or process.stdout.strip()
                or "NCBI Datasets returned an unknown error."
            )

            raise GenomeDownloadError(
                "GenBank download failed: "
                f"{error_message}"
            )

        if not package_path.exists():
            raise GenomeDownloadError(
                "NCBI Datasets did not create the expected "
                "GenBank data package."
            )

        try:
            with zipfile.ZipFile(
                package_path
            ) as package:

                package.extractall(
                    extracted_path
                )

        except (
            OSError,
            zipfile.BadZipFile,
        ) as exc:
            raise GenomeDownloadError(
                "Could not extract the GenBank data package: "
                f"{exc}"
            ) from exc

        data_path = (
            extracted_path
            / "ncbi_dataset"
            / "data"
        )

        for accession in accessions:

            accession_path = (
                data_path
                / accession
            )

            if not accession_path.exists():
                raise GenomeDownloadError(
                    "NCBI Datasets did not return files for "
                    f"{accession}."
                )

            for file_format in (
                supported_formats
            ):

                format_config = (
                    GENBANK_DATASETS_FORMATS[
                        file_format
                    ]
                )

                source_files = (
                    _find_genbank_dataset_files(
                        accession_path,
                        format_config[
                            "patterns"
                        ],
                    )
                )

                for source_file in (
                    source_files
                ):

                    destination_name = (
                        _build_genbank_output_name(
                            accession,
                            source_file,
                        )
                    )

                    destination_file = (
                        destination_path
                        / destination_name
                    )

                    shutil.copy2(
                        source_file,
                        destination_file,
                    )

                    copied_files.append(
                        destination_file
                    )

    return copied_files

def _find_genbank_dataset_files(
    accession_path,
    patterns,
):
    """
    Find files for one requested GenomeSieve format inside
    an extracted NCBI Datasets assembly directory.
    """

    for pattern in patterns:

        matches = sorted(
            accession_path.glob(
                pattern
            )
        )

        if matches:
            return matches

    return []

def _build_genbank_output_name(
    accession,
    source_file,
):
    """
    Build a collision-safe flat filename for a file extracted
    from an NCBI Datasets package.
    """

    source_name = (
        source_file.name
    )

    if source_name.startswith(
        accession
    ):
        return source_name

    return (
        f"{accession}_"
        f"{source_name}"
    )


def _emit_progress(
    callback,
    phase,
    completed,
    total,
    percentage,
    eta_seconds,
    last_item=None,
):
    """
    Send a progress update when a callback was provided.
    """

    if callback is None:
        return

    callback(
        DownloadProgress(
            phase=phase,
            completed=completed,
            total=total,
            percentage=percentage,
            eta_seconds=eta_seconds,
            last_item=last_item,
        )
    )