# Initial validation, 2026-10-11

Environment: host Python 3.12.7 (Windows, MSC v.1929 AMD64). cryptography, pandas, pyarrow, pyspark, matplotlib and pytest were not importable in this host Python. Tests use stdlib unittest, not pytest. No packages or toolchains were installed.

Command: PYTHONPATH=src; python -m unittest discover -s tests -v.
Outcome: 21 methods, 19 passed, 2 skipped: AES-GCM test requires cryptography; Spark test requires opt-in plus PySpark/Java. The multi-configuration correctness method exercised only PLAIN/H-CHAOS, not missing AES paths. PowerShell treated redirected native stderr test output as NativeCommandError records; unittest nevertheless ended OK (skipped=2), and smoke subsequently completed. This shell formatting was not a unit-test failure.

Smoke completed with 12 synthetic rows, 128-bit explicitly test-only keys, PLAIN/H-CHAOS, one warmup and two measured repeats each. results/smoke/run.json holds four authentic samples; summary JSON/CSV/Markdown is computed from those exact samples. They are **not** public-data, Spark, secure-key or publishable performance evidence. results/security.json is a bounded diagnostic run with sensitivity, cycle scan, nonce reuse and restricted state search; NIST full suite is marked pending.

Not run/verified: AES-DEC/H-GCM execution, actual Spark map/reduce, full 2048-bit benchmark, NYC/NSL-KDD input downloads, 10-repeat public measurements, matplotlib chart rendering, TeX/bibtex compilation, independent external bibliography validation, full worker exposure auditing, CPU/RSS metrics or external NIST suite. Parent owns dependencies, GitHub remote and external citation checks; no remote publication was performed.

The initial bounded state-search report found all 4096 candidates compatible with both the eight-byte known prefix and eight-byte held-out prediction, so it did not uniquely recover state. This reflects output ambiguity under the granted high bits and short observation, not a successful full-state attack or a security guarantee. Protected-output canary audit found all 12 synthetic canaries in PLAIN and none in H-CHAOS serialized output; this is limited to the stated byte-scan scope. Two SVG charts are generated directly from actual smoke medians, not guessed values.

## Follow-up cached dependency validation

Using parent-cached uv --no-project --with cryptography runtime, all 22 test methods completed: 21 passed and only the actual Spark integration test was skipped. AES-GCM AAD/tamper/reuse test and all four configuration comparison paths now executed. A new genuine synthetic Python smoke in results/smoke-four-config used 12 records, 128-bit test-only keys, one warmup and two measured repeats for each configuration (8 measured samples), all checked against the independent Decimal oracle. Re-running with --resume returned the same completed samples without executing another sample; unit tests additionally simulated a partial checkpoint and verified preserved records, completion without duplicate repeat pairs, fresh session tracking and mismatch rejection.

No heavy dependency installation was performed here; uv created a small ephemeral cached cryptography environment (3 packages). Parent still owns Java/PySpark/data provisioning and full runs. Secure-size Spark public-data experiments and TeX rendering remain pending. README initial status above is historical, not the latest dependency-enabled result.

## Resumed final checks 2026-10-13
26 test methods: 25 passed, one Spark integration skip. Includes protocol immutability, numeric CSV, process-tree sampler, publication rejection for synthetic results. New smoke-20261013: 12 synthetic rows, 128-bit test-only keys, all four configs, eight measured samples, oracle correctness. Chart generation required matplotlib; rerun supplied it. NIST full suite and actual Spark/public-data experiments remain blocked/pending. No TeX compiler detected in PATH or usual installation folders. Staged files scanned for common secret formats and size limits; no raw datasets/keys/environments included. No original repository was modified; all writes target the new project.
