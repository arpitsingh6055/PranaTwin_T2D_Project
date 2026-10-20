# Data provenance and optional public data

Default source: project-authored synthetic generator, seed 42. Ten days per each of three fictional contexts. No real names, ABHA identifiers or patient files. It is not Synthea output, an ICMR resample, or an Empatica-derived signal. Code and generated synthetic examples are MIT. Dependencies retain their own license notices.

CGMacros v1.0.0 is an optional candidate at https://physionet.org/content/cgmacros/1.0.0/ . Inspect its current Data Description, Files and License sections before download. No dataset copy is included. BIG IDEAs at https://physionet.org/content/big-ideas-glycemic-wearable/ is a candidate with current access/license UNVERIFIED here. Neither dataset contributes any reported metric. No automatic download script bypasses registration or acceptance.

Manual path: obtain the dataset through its official page and accept applicable terms yourself. Preserve original files unchanged under data/raw/<dataset>/<version>/ (gitignored). Record source URL, version, license text/URL, access date and SHA256 in a sidecar manifest. Export an authorized anonymous subject to the contract in ingestion.md, then run `python -m engine.ingest input.csv --source open-source --output data/processed/subject.json`. Do not combine it with synthetic reports. The current API intentionally serves only its deterministic seed; external-file processing does not silently load real data into the app or claim model validation.

Known gap: dataset-specific raw parsers and an external-data evaluation protocol still require an actual authorized dataset and schema inspection. The normalized ingestion contract is tested. No public data performance claims are made.
