# Frozen datasets and preprocessing

## NYC TLC yellow January 2024

Source landing page: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
Exact intended object: https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet

Download this object manually to data/yellow_tripdata_2024-01.parquet, retain its byte-identical original, record UTC download time and URL in your experiment log. The implementation records SHA-256 of the actual input file; it does not pretend to know an independently authoritative checksum. Public-source availability must be checked before download.

Read exactly fare_amount, trip_distance, tip_amount, payment_type, VendorID, tpep_pickup_datetime, tpep_dropoff_datetime, PULocationID, DOLocationID. The first three are aggregation fields; payment_type and VendorID are visible. Timestamps and location IDs are sensitive tuples. Timestamps become ISO strings and pandas missing values become null. Negative fares/refunds are retained. No undocumented outlier removal or payment filtering is performed. Decimal(str(value)) and HALF_EVEN quantization at scale 100 define reference arithmetic, not binary float summation. Distance therefore has two decimal places by design, even if a source carries more precision.

## NSL-KDD

Source/description: https://www.unb.ca/cic/datasets/nsl.html
Obtain the complete KDDTrain+.txt from the dataset's public release or documented archive. Do not substitute KDDTrain+_20Percent.txt, KDDTest+.txt or ARFF silently. Redistribution availability can change; record the exact mirror/release URL, archive checksum, extracted file checksum and access date when using a mirror. Current software accepts a local file and never downloads an unverified mirror.

43 comma-separated fields, no header: 41 features then attack label then difficulty. Full fixed schema is ppbench.datasets.NSL_COLUMNS. duration, src_bytes, dst_bytes become integer aggregation fields. protocol_type is visible. All remaining fields, including service, flag, label and difficulty, are sensitive tuple fields. This aligns with the supplied paper rather than treating service/flag as public. Values beyond the aggregation fields are intentionally preserved as strings.

KDDTrain+ is documented as 125973 records; actual source_rows is recorded. Only 10000, 50000 and 100000 sampled records fit. The 500000 case is unavailable without changing the dataset protocol. Loader raises instead of sampling with replacement. A benchmark claiming 500000 original NSL-KDD training records is invalid under this protocol.

## Sampling and provenance

random.Random(2024).sample chooses deterministic index subsets without replacement; each size is sampled independently from the same frozen row sequence. Record original byte SHA-256, source row count, selected row count, seed and hash of ordered selected indexes. Exact selected indexes are reproducible from source order and the recorded Python version/seed; their SHA-256 confirms reconstruction. Neither public dataset establishes a real confidentiality requirement; sensitive labels are research modeling choices.

Loading currently materializes the entire source dataset before sampling. These loading costs are outside measured stages and may use substantial memory. Do not interpret timing as source ingest performance. Do not run 500000-row 2048-bit protection casually on a limited machine.
