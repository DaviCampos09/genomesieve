import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from genomesieve.services.ncbi_search import GenomeRecord


class GenomeDownloadError(Exception):
    """Raised when genome files cannot be downloaded."""


@dataclass
class GenomeDownloadResult:
    destination: Path
    requested_assemblies: int
    formats: list[str]


def download_genomes(
    records: list[GenomeRecord],
    file_formats: list[str],
    destination: str,
) -> GenomeDownloadResult:
    """
    Download exactly the assemblies selected during the GenomeSieve
    search step.
    """

    downloader_path = shutil.which("ncbi-genome-download")

    if downloader_path is None:
        raise GenomeDownloadError(
            "ncbi-genome-download was not found. "
            "Make sure it is installed and available in PATH."
        )

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

    command = [
        downloader_path,
        "bacteria",
        "--assembly-accessions",
        ",".join(accessions),
        "--formats",
        ",".join(file_formats),
        "--output-folder",
        str(destination_path),
        "--flat-output",
        "--parallel",
        "4",
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
            f"Could not start ncbi-genome-download: {exc}"
        ) from exc

    if process.returncode != 0:
        error_message = (
            process.stderr.strip()
            or process.stdout.strip()
            or "Unknown download error."
        )

        raise GenomeDownloadError(
            f"Genome download failed: {error_message}"
        )

    return GenomeDownloadResult(
        destination=destination_path,
        requested_assemblies=len(records),
        formats=file_formats,
    )