# GenomeSieve

**GenomeSieve** is an open-source desktop application designed to simplify the search, filtering, selection, and download of genome assemblies from the National Center for Biotechnology Information (NCBI).

The project provides a graphical interface for workflows that would otherwise require multiple manual searches, command-line operations, and post-processing steps.

GenomeSieve is particularly intended for researchers and students who need to retrieve multiple genome assemblies while applying consistent filtering and selection criteria.

## Table of Contents

* [Features](#features)
* [Current Scope](#current-scope)
* [Requirements](#requirements)
* [Installing NCBI Datasets](#installing-ncbi-datasets)
* [Installation](#installation)
* [Running GenomeSieve](#running-genomesieve)
* [Basic Workflow](#basic-workflow)

  * [Search by genus](#search-by-genus)
  * [Download genome files](#download-genome-files)
  * [Import assembly accessions from a spreadsheet](#import-assembly-accessions-from-a-spreadsheet)
  * [Export reports](#export-reports)
* [RefSeq and GenBank](#refseq-and-genbank)
* [Third-Party Software](#third-party-software)
* [Limitations](#limitations)
* [License](#license)
* [Citation](#citation)
* [Contributing and Feedback](#contributing-and-feedback)
* [Project Status](#project-status)

## Features

GenomeSieve currently provides:

* Search for genome assemblies by genus.
* RefSeq-based genome search.
* Filtering by assembly level.
* Species-level filtering and assembly selection.
* Control over the number of assemblies selected per species.
* Download of multiple genomic sequence and annotation file formats.
* Spreadsheet import for assembly accession lists.
* Support for both RefSeq (`GCF_`) and GenBank (`GCA_`) accessions through spreadsheet import.
* Spreadsheet validation before downloading.
* Duplicate detection and handling during spreadsheet import.
* Automatic handling of GenBank downloads through NCBI Datasets when required.
* Search and download progress tracking.
* CSV search reports.
* CSV download reports.
* Graphical desktop interface built with PySide6.

## Current Scope

GenomeSieve `v0.1.0` is the first public release of the project.

In the current version, searches initiated directly from the graphical interface use **RefSeq assemblies**.

GenBank assemblies can be processed when assembly accessions are provided through the spreadsheet import workflow.

Some files available through RefSeq do not have direct equivalents in every GenBank download workflow. GenomeSieve informs the user when selected file formats are unavailable and allows the download to continue with the available files.

## Requirements

GenomeSieve requires:

* Python 3.10 or newer.
* NCBI Datasets command-line tool available in the system `PATH`.
* Git, when installing the project by cloning the repository.

Python dependencies such as PySide6, `ncbi-genome-download`, and `openpyxl` are installed automatically during installation.

The initial release has been tested on:

* Linux
* Python 3.12.9
* NCBI Datasets CLI 18.29.1

Other operating systems and software versions may work but have not yet been formally tested.

## Installing NCBI Datasets

GenomeSieve uses the official **NCBI Datasets command-line tool** for genome metadata retrieval, spreadsheet accession validation, and some download operations.

Install NCBI Datasets following the installation instructions provided in the [official NCBI Datasets documentation](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/command-line-tools/download-and-install/?utm_source=chatgpt.com) .

After installation, verify that the command is available:

```bash
datasets version
```

GenomeSieve expects the `datasets` executable to be available in your system `PATH`.

NCBI Datasets is updated frequently. GenomeSieve was tested with version `18.29.1`, but installation of the current supported NCBI version is recommended.

## Installation

Clone the repository:

```bash
git clone https://github.com/DaviCampos09/genomesieve.git
cd genomesieve
```

Create a Python virtual environment:

```bash
python3 -m venv .venv
```

Activate it on Linux/macOS:

```bash
source .venv/bin/activate
```

Then install GenomeSieve:

```bash
python -m pip install .
```

The installation process automatically installs the required Python dependencies.

## Running GenomeSieve

After installation, start the application with:

```bash
genomesieve
```

The graphical interface should open automatically.

The application can also be started directly as a Python module:

```bash
python -m genomesieve.main
```

## Basic Workflow

### Search by genus

Enter a genus name in the search interface and configure the desired search parameters.

GenomeSieve retrieves the corresponding assembly metadata from NCBI and applies the selected filtering criteria.

After the search finishes, review the resulting assemblies and choose the desired download options.

### Download genome files

Select the desired file formats and choose an output directory.

GenomeSieve prepares the selected assemblies, downloads the corresponding files, and reports download progress through the graphical interface.

### Import assembly accessions from a spreadsheet

GenomeSieve can also process assembly accessions supplied through spreadsheet files.

This workflow supports both:

* RefSeq accessions (`GCF_`)
* GenBank accessions (`GCA_`)

The user can select the spreadsheet sheet and accession column, inspect validation results, handle duplicate entries, and proceed with the validated assemblies.

### Export reports

GenomeSieve can generate CSV reports containing information about search results and download operations.

These reports can be used to keep a record of the assemblies identified, selected, and downloaded during a workflow.

## RefSeq and GenBank

GenomeSieve interacts with both RefSeq and GenBank assemblies, but their use differs in the current release.

Direct genus searches currently operate on **RefSeq**.

Spreadsheet-based workflows may contain both RefSeq (`GCF_`) and GenBank (`GCA_`) accessions.

Depending on the assembly source and selected file format, GenomeSieve may use different NCBI retrieval mechanisms. When a requested format is not available for a particular GenBank workflow, the application informs the user before continuing.

## Third-Party Software

GenomeSieve uses or interoperates with several third-party projects, including:

* NCBI Datasets
* ncbi-genome-download
* PySide6 / Qt for Python
* openpyxl

Information about these components and their respective licenses is available in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

GenomeSieve is an independent project and is not affiliated with, maintained by, sponsored by, or endorsed by NCBI, The Qt Company, or the developers of the third-party software used by the application.

## Limitations

GenomeSieve is currently an early public release.

Important limitations of `v0.1.0` include:

* Direct genus searches currently use RefSeq only.
* GenBank support is primarily available through spreadsheet accession import.
* Some file formats may not be available for all GenBank assemblies.
* The application currently depends on the external NCBI Datasets CLI.
* The initial release has only been formally tested on Linux.
* Changes to external NCBI services or command-line tools may affect some GenomeSieve functionality.

Feedback and bug reports are welcome and can help improve future releases.

## License

GenomeSieve is distributed under the **Apache License 2.0**.

See [LICENSE](LICENSE) for the complete license text.

Third-party software remains subject to its respective licenses. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for additional information.

## Citation

GenomeSieve is currently in its initial public release.

A formal software citation will be added if/when an associated publication or archived software release becomes available.

Until then, academic users may reference the GenomeSieve repository and the specific software version used in their work.

## Contributing and Feedback

GenomeSieve is under active development.

Bug reports, feature suggestions, and feedback about real-world genome retrieval workflows are welcome through the repository's issue tracker.

Contributions can also be proposed through pull requests.

## Project Status

**Current version:** `0.1.0`

GenomeSieve is functional and ready for initial public use, but should still be considered an early-stage scientific software project.
