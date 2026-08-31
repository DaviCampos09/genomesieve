import json
import re
import shutil
import subprocess
from dataclasses import dataclass


ANNOTATION_DEPENDENT_FORMATS = {
    "protein-fasta",
    "cds-fasta",
    "rna-fasta",
    "gff",
    "genbank",
    "translated-cds",
}


class GenomeSearchError(Exception):
    """Raised when a genome search cannot be completed."""


@dataclass(frozen=True)
class GenomeRecord:
    accession: str
    species: str | None
    organism_name: str
    refseq_category: str
    assembly_level: str


@dataclass
class GenomeSearchResult:
    all_records: list[GenomeRecord]
    selected_records: list[GenomeRecord]

    total_assemblies: int
    identified_species: int
    unidentified_assemblies: int

    selected_assemblies: int
    selected_species: int
    selected_reference_genomes: int


def search_genomes(
    genus: str,
    assembly_levels: list[str],
    file_formats: list[str],
    keep_one_per_species: bool,
    remove_unidentified: bool,
) -> GenomeSearchResult:
    """
    Search NCBI RefSeq genome metadata for a genus and apply the
    GenomeSieve selection rules without downloading sequence files.
    """

    datasets_path = shutil.which("datasets")

    if datasets_path is None:
        raise GenomeSearchError(
            "NCBI Datasets was not found. "
            "Make sure the 'datasets' command is installed and available in PATH."
        )

    if not assembly_levels:
        raise GenomeSearchError(
            "Select at least one assembly level."
        )

    command = [
        datasets_path,
        "summary",
        "genome",
        "taxon",
        genus,
        "--assembly-level",
        ",".join(assembly_levels),
        "--assembly-source",
        "RefSeq",
        "--limit",
        "all",
        "--as-json-lines",
    ]

    # Formats such as Protein FASTA, CDS and GFF require genome
    # annotation. In these cases, restrict the search to annotated
    # assemblies.
    if set(file_formats) & ANNOTATION_DEPENDENT_FORMATS:
        command.append("--annotated")

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

    except OSError as exc:
        raise GenomeSearchError(
            f"Could not start NCBI Datasets: {exc}"
        ) from exc

    if process.returncode != 0:
        error_message = process.stderr.strip()

        if not error_message:
            error_message = "NCBI returned an unknown error."

        raise GenomeSearchError(
            f"Genome search failed: {error_message}"
        )

    records = _parse_datasets_output(process.stdout)

    selected_records = _select_records(
        records,
        keep_one_per_species=keep_one_per_species,
        remove_unidentified=remove_unidentified,
    )

    identified_species = {
        record.species
        for record in records
        if record.species is not None
    }

    unidentified_assemblies = sum(
        1
        for record in records
        if record.species is None
    )

    selected_species = {
        record.species
        for record in selected_records
        if record.species is not None
    }

    selected_reference_genomes = sum(
        1
        for record in selected_records
        if record.refseq_category.lower() == "reference genome"
    )

    return GenomeSearchResult(
        all_records=records,
        selected_records=selected_records,
        total_assemblies=len(records),
        identified_species=len(identified_species),
        unidentified_assemblies=unidentified_assemblies,
        selected_assemblies=len(selected_records),
        selected_species=len(selected_species),
        selected_reference_genomes=selected_reference_genomes,
    )


def _parse_datasets_output(output: str) -> list[GenomeRecord]:
    records = []

    for line in output.splitlines():
        line = line.strip()

        if not line:
            continue

        try:
            data = json.loads(line)

        except json.JSONDecodeError as exc:
            raise GenomeSearchError(
                "NCBI returned an unexpected response."
            ) from exc

        # Normally --as-json-lines returns one assembly per line,
        # but this also supports a response wrapped in "reports".
        reports = data.get("reports")

        if isinstance(reports, list):
            raw_records = reports
        else:
            raw_records = [data]

        for raw_record in raw_records:
            record = _parse_record(raw_record)

            if record is not None:
                records.append(record)

    return records


def _parse_record(data: dict) -> GenomeRecord | None:
    accession = _get_value(
        data,
        "accession",
        "currentAccession",
        "current_accession",
    )

    if not accession:
        return None

    organism = _get_value(
        data,
        "organism",
    ) or {}

    assembly_info = _get_value(
        data,
        "assemblyInfo",
        "assembly_info",
    ) or {}

    ani = _get_value(
        data,
        "averageNucleotideIdentity",
        "average_nucleotide_identity",
    ) or {}

    organism_name = _get_value(
        organism,
        "organismName",
        "organism_name",
    ) or ""

    submitted_species = _get_value(
        ani,
        "submittedSpecies",
        "submitted_species",
    )

    species = _normalize_species(submitted_species)

    refseq_category = _get_value(
        assembly_info,
        "refseqCategory",
        "refseq_category",
    ) or "na"

    assembly_level = _get_value(
        assembly_info,
        "assemblyLevel",
        "assembly_level",
    ) or "Unknown"

    return GenomeRecord(
        accession=accession,
        species=species,
        organism_name=organism_name,
        refseq_category=refseq_category,
        assembly_level=assembly_level,
    )


def _get_value(data: dict, *keys):
    for key in keys:
        if key in data:
            return data[key]

    return None


def _normalize_species(species: str | None) -> str | None:
    """
    Return None when the species is missing or not identified to the
    species level.
    """

    if not species:
        return None

    species = species.strip()

    if not species:
        return None

    if species.lower() in {"na", "unknown"}:
        return None

    unidentified_patterns = [
        r"(?:^|\s)sp\.(?:\s|$)",
        r"\buncultured\b",
        r"\bunclassified\b",
        r"\bunidentified\b",
        r"\bunknown\b",
    ]

    for pattern in unidentified_patterns:
        if re.search(
            pattern,
            species,
            flags=re.IGNORECASE,
        ):
            return None

    return species


def _select_records(
    records: list[GenomeRecord],
    keep_one_per_species: bool,
    remove_unidentified: bool,
) -> list[GenomeRecord]:

    if not keep_one_per_species:
        if remove_unidentified:
            return [
                record
                for record in records
                if record.species is not None
            ]

        return list(records)

    best_by_species = {}
    unidentified_records = []

    for record in records:

        # Unknown species cannot safely be deduplicated because we
        # cannot assume two "Genus sp." records are the same species.
        if record.species is None:

            if not remove_unidentified:
                unidentified_records.append(record)

            continue

        current_best = best_by_species.get(record.species)

        if current_best is None:
            best_by_species[record.species] = record
            continue

        if _record_priority(record) > _record_priority(current_best):
            best_by_species[record.species] = record

    return list(best_by_species.values()) + unidentified_records


def _record_priority(record: GenomeRecord) -> tuple[int, int]:
    """
    GenomeSieve automatic priority.

    RefSeq category:
        Reference Genome > Representative Genome > Other

    Assembly level:
        Complete Genome > Chromosome > Scaffold > Contig
    """

    refseq_priority = {
        "reference genome": 3,
        "representative genome": 2,
    }

    assembly_priority = {
        "complete genome": 4,
        "chromosome": 3,
        "scaffold": 2,
        "contig": 1,
    }

    refseq_score = refseq_priority.get(
        record.refseq_category.lower(),
        1,
    )

    assembly_score = assembly_priority.get(
        record.assembly_level.lower(),
        0,
    )

    return refseq_score, assembly_score