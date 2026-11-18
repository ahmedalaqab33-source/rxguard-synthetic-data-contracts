# RxGuard Synthetic Data Contracts

Small Python/SQL research-software contracts for testing how tabular evidence is linked,
timed and represented before clinical interpretation. Author: **Ahmed Alaqab**.

**Development status: experimental engineering toolkit, synthetic examples only.**
It is not a clinical decision system, an AKI phenotype, a dosing method or a validated
clinical data pipeline. The internal clinical acceptance and model-training holds remain.

## Problem and workflow

Joins can silently multiply rows, missing keys can be confused with matches, and event
time can be mistaken for information availability. The modules make these distinctions
explicit on small invented inputs, with assertions and aggregate checks.

| Module | Implemented scope |
| --- | --- |
| `tools/clinical_data_contract_v1` | Dictionary/event no-fanout joins; eMAR composite-key partitions; admission-level order/detail coverage; Python/SQL and base-R arithmetic |
| `tools/medication_linkage_synthetic_v1` | Three-key prescription/pharmacy candidate linkage, ambiguity and half-open interval overlap |
| `tools/creatinine_synthetic_v1` | Decimal pairwise temporal threshold arithmetic; no baseline selection, AKI diagnosis, staging or clinical validation |
| `tools/evidence_trace_synthetic_v1` | Timezone-aware availability and source-assertion checks; digest shape does not authenticate origin |
| `tools/parallel_readiness_v1` | Metadata-only inventory checkpoint planning; never opens candidate clinical data or permits integration |
| `02_code/validation` | Shared SQL used by the admission-level invented-data contract |

Modules are retained in their existing layout to preserve exact source bytes and shared
SQL paths. They are related components of one toolkit, not separate scientific studies.

## Requirements and setup

Python 3.10+ syntax is used; the distribution is verified locally on Python 3.13.16,
DuckDB 1.5.6 and optional base R 4.6.1. Other platforms/runtime combinations are unverified.
Use a separate environment if installing dependencies; no automatic installation occurs.

```text
python -m pip install -r requirements.txt
python -B run_tests.py
```

These tests use invented inputs. They do not load MIMIC, fit a clinical model or download data.
See [verification](docs/VERIFICATION.md) for the exact locally observed results.

## Example execution and inputs/outputs

From the repository root, choose a **new external** output path:

```text
python -B tools/clinical_data_contract_v1/run_contract.py --output ../contract-example --rscript /path/to/Rscript
python -B tools/clinical_data_contract_v1/run_emar_linkage_v1.py --output ../emar-example
python -B tools/clinical_data_contract_v1/run_admission_medication_coverage_v1.py --output ../coverage-example
```

The first command compares 24 aggregate metrics between Python/SQL and base R. The other
commands run their module tests and write explicitly invented fixture/count receipts.
These runners refuse existing output directories; supply Rscript explicitly for portability.
For Windows, use the actual Rscript.exe path and quote paths containing spaces.

Pure modules accept in-memory dictionaries/lists with documented source-code schemas.
The planner accepts a small metadata CSV (`table,filename,path,size_bytes,inventory_status`)
and returns checkpoints with `integration_permitted=false`. Keep any private inventory and
its output local. Synthetic markers are assertions, not a proof of anonymization.

## Validation and limits

Tests cover key ambiguity, nulls, cardinality, timing boundaries, literal units, malformed
inputs, nonmutation and deterministic output. A unique key match or positive interval
does not prove a medication was administered. An unflagged trace is not a clinical safety
verdict. Pairwise creatinine arithmetic does not select references or assess observation
sufficiency. Clinical schema adaptation, exposure/endpoint adjudication and large-scale
performance remain outside this release. No clinical observations or effect estimates
are presented. No hosted-CI or independent-human replication is claimed.

## Data, attribution and maintenance

[DATA_AVAILABILITY.md](DATA_AVAILABILITY.md) defines the release boundary. Only two small,
explicitly invented JSON fixtures are distributed; numerical IDs and future dates in them
are artificial. No clinical source/derived data, reference corpus or manuscript is included.
[SOURCE_PROVENANCE.json](SOURCE_PROVENANCE.json) records preserved source hashes.

MIT license, copyright Ahmed Alaqab. Cite the repository and exact commit using
[CITATION.cff](CITATION.cff); no DOI or peer-reviewed publication is claimed.
For maintenance and reproducible bug reports, use this repository's GitHub Issues.
