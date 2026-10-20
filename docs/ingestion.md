# Normalized wearable ingestion contract

CSV header: timestamp,glucose,unit,hr,hrv,eda,temperature,activity,carbs. Required: timestamp and unit. Use ISO8601 explicit offset; mg/dL. Empty glucose/auxiliary signals remain null; never backfill from future values. Missing meal/activity defaults to zero g/one proxy unit only when explicitly representing no logged event; if event logging is unavailable record that limitation in source manifest.

Rows must be ordered and unique. Input range validation is Packet schema in model.py. Sampling irregularities and missing signals become quality flags. Gaps over one day are rejected. Original file remains unchanged; output includes SHA256, source, transformation timestamp and per-row quality. Converted timestamps retain offset; comparisons are absolute instants. The importer does not infer glucose from HR or resample high-frequency raw biosignals.

For raw high-frequency signals, aggregate only trailing samples at or before the five-minute timestamp. Do not interpolate through future observations. Dataset-specific mapping must document actual columns and units; unsupported signals remain missing. IBI-to-RMSSD and accelerometry-to-MET conversion are not implemented and are not claimed.
