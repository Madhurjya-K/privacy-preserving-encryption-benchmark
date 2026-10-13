# Measured samples: synthetic/Python smoke only; NOT Spark or publishable public-data evidence

| Configuration | Metric | Median | IQR | Bootstrap 95% CI | n |
|---|---|---:|---:|---|---:|
|H-CHAOS|protection_sec|0.144185|0.00434605|[0.139839, 0.148531]|2|
|H-CHAOS|integrity_verification_sec|0.00324595|0.00091295|[0.002333, 0.0041589]|2|
|H-CHAOS|query_sec|0.0015867|0.0002362|[0.0013505, 0.0018229]|2|
|H-CHAOS|final_decryption_sec|0.0135117|0.00414105|[0.0093707, 0.0176528]|2|
|H-CHAOS|serialization_sec|0.0021255|6.58e-05|[0.0020597, 0.0021913]|2|
|H-CHAOS|hashing_sec|8.065e-05|5.05e-06|[7.56e-05, 8.57e-05]|2|
|H-CHAOS|protected_bytes|9311.5|1.5|[9310, 9313]|2|
|H-CHAOS|protection_peak_python_bytes|40445.5|0.5|[40445, 40446]|2|
|H-CHAOS|query_peak_python_bytes|4628|0|[4628, 4628]|2|
|H-CHAOS|end_to_end_sec|0.164735|0.000411|[0.164324, 0.165146]|2|
|H-CHAOS|throughput_records_per_sec|72.8446|0.181741|[72.6629, 73.0264]|2|
|H-CHAOS|size_expansion|2.81655|0.000453721|[2.81609, 2.817]|2|
|PLAIN|protection_sec|0.00635505|0.00077595|[0.0055791, 0.007131]|2|
|PLAIN|integrity_verification_sec|0.00527235|0.00175395|[0.0035184, 0.0070263]|2|
|PLAIN|query_sec|0.00308215|0.00034615|[0.002736, 0.0034283]|2|
|PLAIN|final_decryption_sec|0.000386|8e-07|[0.0003852, 0.0003868]|2|
|PLAIN|serialization_sec|0.00235905|0.00102425|[0.0013348, 0.0033833]|2|
|PLAIN|hashing_sec|9.92e-05|1.96e-05|[7.96e-05, 0.0001188]|2|
|PLAIN|protected_bytes|4166|0|[4166, 4166]|2|
|PLAIN|protection_peak_python_bytes|15365|12|[15353, 15377]|2|
|PLAIN|query_peak_python_bytes|4560|0|[4560, 4560]|2|
|PLAIN|end_to_end_sec|0.0175538|0.0039207|[0.0136331, 0.0214745]|2|
|PLAIN|throughput_records_per_sec|719.506|160.704|[558.802, 880.211]|2|
|PLAIN|size_expansion|1.26013|0|[1.26013, 1.26013]|2|
|H-CHAOS|end_to_end_overhead_percent_vs_PLAIN|888.284|223.078|[665.206, 1111.36]|2|
|PLAIN|end_to_end_overhead_percent_vs_PLAIN|0|0|[0, 0]|2|