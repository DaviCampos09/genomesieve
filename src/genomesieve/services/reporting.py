import csv
from datetime import datetime
from pathlib import Path

from genomesieve.services.ncbi_search import GenomeSearchResult

from genomesieve.services.ncbi_download import (
    GENBANK_UNSUPPORTED_FILE_FORMATS,
)


class ReportError(Exception):
    """Raised when a GenomeSieve report cannot be generated."""


def export_search_report(
    result: GenomeSearchResult,
    output_path: str,
    genus: str,
    assembly_levels: list[str],
    file_formats: list[str],
    keep_one_per_species: bool,
    remove_unidentified: bool,
):
    """
    Export all assemblies returned by the search and explain whether
    each assembly was selected or discarded.
    """

    path = Path(output_path)

    selected_accessions = {
        record.accession
        for record in result.selected_records
    }

    timestamp = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    selection_strategy = (
        "one_per_species"
        if keep_one_per_species
        else "keep_all"
    )

    fieldnames = [
        "search_timestamp",
        "genus",
        "assembly_levels",
        "requested_formats",
        "selection_strategy",
        "remove_unidentified",
        "accession",
        "species",
        "organism_name",
        "refseq_category",
        "assembly_level",
        "selection_status",
        "selection_reason",
    ]

    try:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as csv_file:

            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            for record in result.all_records:

                status, reason = _get_selection_explanation(
                    record=record,
                    selected_accessions=selected_accessions,
                    keep_one_per_species=keep_one_per_species,
                    remove_unidentified=remove_unidentified,
                )

                writer.writerow(
                    {
                        "search_timestamp": timestamp,
                        "genus": genus,
                        "assembly_levels": "|".join(
                            assembly_levels
                        ),
                        "requested_formats": "|".join(
                            file_formats
                        ),
                        "selection_strategy": selection_strategy,
                        "remove_unidentified": (
                            remove_unidentified
                        ),
                        "accession": record.accession,
                        "species": record.species or "",
                        "organism_name": (
                            record.organism_name
                        ),
                        "refseq_category": (
                            record.refseq_category
                        ),
                        "assembly_level": (
                            record.assembly_level
                        ),
                        "selection_status": status,
                        "selection_reason": reason,
                    }
                )

    except OSError as exc:
        raise ReportError(
            f"Could not save search report: {exc}"
        ) from exc

    return path


def export_download_report(
    records,
    destination,
    source_type,
    source_name,
    file_formats,
    output_path,
):
    destination_path = Path(
        destination
    )

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = (
        datetime.now()
        .astimezone()
        .isoformat(
            timespec="seconds"
        )
    )

    fieldnames = [
        "download_timestamp",
        "source_type",
        "source_name",
        "accession",
        "assembly_source",
        "species",
        "organism_name",
        "refseq_category",
        "assembly_level",
        "requested_formats",
        "unavailable_requested_formats",
        "files_present",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for record in records:

            files = _find_assembly_files(
                destination=destination_path,
                accession=record.accession,
            )

            assembly_source = (
                _get_assembly_source(
                    record.accession
                )
            )

            unavailable_formats = (
                _get_unavailable_requested_formats(
                    accession=record.accession,
                    file_formats=file_formats,
                )
            )

            writer.writerow(
                {
                    "download_timestamp": timestamp,
                    "source_type": source_type,
                    "source_name": source_name,
                    "accession": record.accession,
                    "assembly_source": (
                        assembly_source
                    ),
                    "species": (
                        record.species or ""
                    ),
                    "organism_name": (
                        record.organism_name
                    ),
                    "refseq_category": (
                        record.refseq_category
                    ),
                    "assembly_level": (
                        record.assembly_level
                    ),
                    "requested_formats": (
                        ",".join(
                            file_formats
                        )
                    ),
                    "unavailable_requested_formats": (
                        ",".join(
                            unavailable_formats
                        )
                    ),
                    "files_present": (
                        ",".join(
                            files
                        )
                    ),
                }
            )


def _get_selection_explanation(
    record,
    selected_accessions,
    keep_one_per_species,
    remove_unidentified,
):
    """
    Explain why an assembly was selected or excluded.
    """

    if record.accession in selected_accessions:

        if record.species is None:
            return (
                "selected",
                "Unidentified assembly retained by user settings",
            )

        if keep_one_per_species:
            return (
                "selected",
                "Best available assembly for species",
            )

        return (
            "selected",
            "All assemblies retained by selection strategy",
        )

    if (
        record.species is None
        and remove_unidentified
    ):
        return (
            "removed_unidentified",
            "Species could not be identified",
        )

    if keep_one_per_species:
        return (
            "not_selected",
            (
                "Higher-priority assembly available "
                "for the same species"
            ),
        )

    return (
        "not_selected",
        "Excluded by selection rules",
    )


def _find_assembly_files(
    destination: Path,
    accession: str,
):
    """
    Return downloaded files whose name begins with the assembly
    accession.
    """

    files = []

    for path in destination.glob(
        f"{accession}*"
    ):
        if path.is_file():
            files.append(
                path.name
            )

    return sorted(files)

def _get_assembly_source(
    accession: str,
):
    """
    Return the NCBI assembly collection used for download.
    """

    if accession.startswith(
        "GCF_"
    ):
        return "RefSeq"

    if accession.startswith(
        "GCA_"
    ):
        return "GenBank"

    return "Unknown"


def _get_unavailable_requested_formats(
    accession: str,
    file_formats: list[str],
):
    """
    Return requested formats that GenomeSieve cannot obtain
    for a GenBank-only assembly.
    """

    if not accession.startswith(
        "GCA_"
    ):
        return []

    return [
        file_format
        for file_format
        in file_formats
        if file_format
        in GENBANK_UNSUPPORTED_FILE_FORMATS
    ]

def _safe_filename(value: str):
    """
    Convert a genus name into a safe filename component.
    """

    return "".join(
        character
        if character.isalnum()
        else "_"
        for character in value.strip()
    ).strip("_")