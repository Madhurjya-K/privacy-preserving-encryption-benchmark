# Privacy-Preserving Hybrid Encryption Benchmark

Authors: **Madhurjya Kakati and Gracy Sonwan**.

Research implementation of the attached design paper, not production cryptography. Public-dataset experiments on actual local Spark are **pending**. Synthetic Python smoke results are not cloud scalability evidence. H-CHAOS is experimental masking, not an established secure cipher.

## What is implemented

- Four configurations: PLAIN, AES-DEC, H-CHAOS, H-GCM.
- Raw-integer Paillier with fresh coprime randomizers; default 2048-bit modulus, signed fixed-point HALF_EVEN encoding and mandatory aggregate range preflight. A middle-third decoding sentinel catches some overflow, but cannot replace the bound check.
- AES-256-GCM records with 96-bit nonce and record-ID AAD. Hybrid sensitive tuples are separate from encrypted numeric fields.
- Exact integer logistic recurrence, SHA-256 key/nonce derivation, zero-state retry, 1024 discarded iterates, specified byte extraction.
- Canonical partition SHA-256 and HMAC manifest authenticating owner, current version, metadata and partition indexes/counts. Within-partition permutations are intentionally canonicalized and **not detected**. Cross-partition movement and rollback are tested.
- Actual optional Spark RDD map/reduce modular multiplication; Python smoke is a distinct backend, never silently substituted. AES-DEC explicitly sends its AES key to baseline workers; hybrid workers receive no private key.
- Grouped and global SUM, COUNT(*) and AVG workloads. AVG uses non-null numeric count, not COUNT(*). All-null SUM/AVG return null. Null ciphertext absence reveals missingness. Hidden-field grouping/predicates are unsupported.
- Raw stage samples, environmental/dataset provenance, separate keygen, serialization/hash controls, Python allocation peaks, protected-byte sizes, seeded median/IQR/bootstrap CI summaries, tables and dependency-free measured SVG charts.
- Bounded sensitivity, short-cycle scans, nonce-reuse demonstration and explicitly privileged partial-state search. The full external NIST SP 800-22 suite is pending; these diagnostics are not NIST tests.

## Installation

Python >=3.10. Use a fresh environment in this directory, never an existing repository. From PowerShell:

~~~powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
# Optional data/Spark/charts extras; Spark additionally requires a supported Java runtime.
python -m pip install -e ".[data,spark,charts]"
$env:PYTHONPATH = "$PWD/src"
python -m unittest discover -s tests -v
~~~

The basic package requires cryptography. If it is unavailable, the standard-library PLAIN/H-CHAOS tests and smoke subset can run directly with PYTHONPATH; AES tests are explicitly skipped, not claimed as passing. No dependency installation was performed in the initial run.

## Small smoke (not research results)

~~~powershell
$env:PYTHONPATH = "$PWD/src"
python -m ppbench.cli smoke --rows 12 --bits 128 --repeats 2 --configs PLAIN H-CHAOS --output results/smoke
python -m ppbench.cli report results/smoke/run.json --output results/smoke/summary
python -m ppbench.cli security --output results/security.json
~~~

After installing cryptography, omit --configs to test all four. Smoke permits deliberately insecure short Paillier keys, labels itself unpublishable, and caps rows at 100. Production benchmark refuses keys below 2048 bits.

## Public-data protocol (not yet run)

See [dataset instructions](docs/DATASETS.md). Download manually, retain the original file, and record download date/source independently. No download, upload, publication or large experiment is automatic.

~~~powershell
python -m ppbench.cli benchmark --dataset nyc --path data/yellow_tripdata_2024-01.parquet --size 10000 --output results/public/nyc-10000
python -m ppbench.cli benchmark --dataset nslkdd --path "data/KDDTrain+.txt" --size 10000 --output results/public/nsl-10000
python -m ppbench.cli report results/public/nyc-10000/run.json --output results/public/nyc-10000/summary --charts
# Real Spark integration test is separately opt-in:
$env:PPBENCH_TEST_SPARK='1'
python -m unittest discover -s tests -p test_spark.py -v
~~~

Default backend is actual Spark local[*], 2048 bits, 10 measured repeats after one warmup per configuration. Sizes are 10000, 50000, 100000, 500000, seed 2024, sampling without replacement. NSL-KDD KDDTrain+ contains fewer than 500000 records; that case must be skipped rather than fabricated by replication. Controls are recorded, not subtracted. Query time combines grouped and global workloads, each scanning data; final decryption combines their results. Manifest construction is included in protection, and verification is a separate stage. End-to-end is a sum of stage times, not a wall-clock measurement including setup/GC/controls or network transfer.

## Initial validation status

Python 3.12.7 on Windows: 21 unittest test methods executed, 19 passed, 2 explicitly skipped (cryptography missing and Spark integration opt-in). The correctness method exercised PLAIN/H-CHAOS only; AES configurations inside it were absent. Synthetic smoke: 12 records, 128-bit test-only keys, 2 measured repeats + 1 warmup for each of PLAIN/H-CHAOS; 4 raw samples. Actual values are in results/smoke/run.json and summary, not invented manuscript results. See [validation log](docs/VALIDATION.md).

## Important boundaries

This local harness holds owner keys on the driver, not in a hardened service. It is not an audited remote deployment. Python tracemalloc excludes native cryptography allocations, JVM and worker memory; it must not be presented as full peak system RSS. No CPU utilization metric or network transfer timing is currently measured. Configurations execute in fixed order, so thermal/order effects remain a limitation; bootstrap CIs describe recorded samples, not eliminate bias. The authenticated manifest verifies stored data, not a maliciously incorrect aggregate. Bounds metadata exposes upper bounds on absolute values in addition to visible groups, lengths, row counts and missingness. Bound canary scans are not a proof of zero worker plaintext exposure. See [security](docs/SECURITY.md) and [methodology](docs/METHODOLOGY.md).

Manuscript: paper/main.tex with paper/references.bib. It is standalone IEEEtran source, not dependent on a prior repository or local figures. Build with an installed TeX distribution using pdflatex, bibtex, pdflatex twice. Bibliographic entries are inherited from the supplied paper or standards; independent external verification belongs to the parent workflow. Rendering and citation completeness need validation before submission.

All rights reserved pending an explicit authors' license decision. Nothing was published to GitHub.

## Resume after interruption

Every completed measured sample is atomically written to checkpoint.json using flush/fsync plus replacement. The current sample is also marked before execution; interruption restarts only that unfinished sample. Re-run the identical command with --resume and the same output directory. Parameters and dataset provenance must exactly match. Existing checkpoints are never overwritten implicitly: choose a new directory for a new experiment. A completed --resume command returns stored samples without rerunning them.

Resumed execution creates fresh keys (no private keys are persisted), records a separate keygen/environment session, keeps completed sample records byte-for-byte as JSON values, and reruns warmups for unfinished configurations. Session-index labels allow separation of resumed timing batches. Since each sample encrypts afresh, equality of private keys across sessions is not needed; key sizes/protocol must match. Freeze dependencies and hardware across sessions or report differences. Progress events are printed with flush after sample start/completion. Checkpoint is research bookkeeping, not a signed provenance certificate.

Spark controls: set PPBENCH_SPARK_MASTER (default local[*]) and PPBENCH_SPARK_DRIVER_MEMORY (default 4g) before startup; parent must set JAVA_HOME, PATH and PYSPARK_PYTHON consistently. 500000-row Paillier runs can require many GB and long execution. Native heaps remain excluded from tracemalloc. NYC source reading uses a dataframe, but only sampled rows are converted to dictionaries, reducing avoidable object memory.

## Latest dependency-enabled validation

Parent-cached cryptography runtime: 22 unittest methods, 21 passed, 1 skipped (actual Spark). All four configurations and AES-GCM AAD/tamper/nonce tests now executed. results/smoke-four-config holds eight genuine 12-record Python samples, plus tables/charts/checkpoint; completed --resume produced no extra samples. These still use insecure test-only 128-bit keys and remain nonpublishable synthetic smoke. The earlier dependency-free status is historical.

## Resumed validation (2026-10-13)

Fresh dependency-enabled unit run: 22 tests, 21 passed and actual Spark test skipped. Java17 portable distribution downloaded and checksum verified. PySpark3.5.3 distribution download repeatedly timed out; uv pip calls returned without installed packages, so do not assume the empty .venv is ready. Use documented pip installation on a normal local Python, or managed uv run with requirements. NYC official file download also timed out. NSLKDD mirror input was obtained and checked, but no public-data benchmark has completed. Full matrix, NIST external suite, log/spill exposure audit, TeX compilation and venue/affiliation confirmation remain pending. See docs/REFERENCE-CHECKS.md.

Matrix planning: python scripts/run_experiments.py --plan-only
Actual matrix: python scripts/run_experiments.py --resume --keep-going (omit --resume for a new output).
Summaries: python scripts/summarize_results.py results/public-matrix --output results/processed
Paper table: python scripts/generate_latex_results.py results/public-matrix --output paper/generated-results.tex (rejects synthetic or incomplete runs).

Linux/macOS setup: python3 -m venv .venv; source .venv/bin/activate; python -m pip install -r requirements.txt; python -m pip install -e .; export PYTHONPATH="$PWD/src"; python -m unittest discover -s tests -v. Java17 JAVA_HOME must point to your installation; Windows command equivalents appear above.

Final resumed test count: 26 methods, 25 passed and one actual-Spark integration skip. Results/smoke-20261013 contains the refreshed four-configuration smoke, real sampled driver RSS/CPU metrics and generated summaries. These are still nonpublishable Python/synthetic/insecure-key measurements.
