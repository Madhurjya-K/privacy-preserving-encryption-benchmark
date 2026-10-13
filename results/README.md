# Recorded evidence

- smoke and smoke-four-config: historical synthetic Python checks with insecure test-only keys.
- smoke-20261013: refreshed 12-row four-configuration Python run, two measured repeats each; resource metrics, CSV, SVG and PNG summaries. Not publication evidence.
- validation-2048-synthetic: 12-row four-configuration Python correctness at 2048 bits, one measured repeat each. Not Spark/public-data evidence.
- security*.json: bounded tamper/sensitivity/cycle/nonce-reuse/privileged-state-search diagnostics. Full NIST suite remains pending.
- validation: real unit-test logs with explicit skips. Historical logs do not supersede resumed tests.
- matrix-plan-20261013: planned cells and blocked/unavailable inputs, NOT executed benchmark results.

Full benchmark outputs belong under results/public-matrix (ignored). Raw data belongs under data/external (ignored). Summaries never invent values. Manuscript result generation rejects synthetic, non-Spark, short-key, incomplete or undersampled runs; the metadata gate is not an independent certification.
