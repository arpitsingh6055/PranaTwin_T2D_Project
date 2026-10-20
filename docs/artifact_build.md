# Rebuilding submission artifacts

`python -m scripts.build_figures` regenerates the sample synthetic FHIR document, architecture PDF and measured evaluation figure using reportlab. The editable flow is also in architecture.mmd. Run evaluation first when the model/data change.

`scripts/build_deck.mjs` is editable presentation source using the Codex bundled @oai/artifact-tool. Set ARTIFACT_TOOL_ROOT to its package directory, PRESENTATION_SKILL_DIR to the installed presentations skill, RUNTIME_NODE_MODULES to bundled Node packages and RUNTIME_PYTHON to the bundled Python executable. Then run `node scripts/build_deck.mjs`. The finalizer intentionally refuses to overwrite an existing final presentation; select a new output name in the script for revisions. The app itself does not require these artifact-authoring tools.

The deck's quantitative chart uses actual reports/metrics.json values and an embedded editable workbook. Source notes accompany every slide. Validation checks package integrity, geometry, fonts and native chart data, then imports the final package with the authoring tool. It has not been opened in native PowerPoint in this environment.

The PDF deck is a viewing copy assembled from rendered slides, with an editable PPTX provided separately. To regenerate a vector/text PDF with PowerPoint, open the PPTX, choose File > Export > Create PDF/XPS, publish all slides, then inspect the exported PDF. LibreOffice, when installed, can also export with `soffice --headless --convert-to pdf --outdir presentation presentation/project_presentation.pptx` (use a new output directory to avoid collision).

Screenshots: launch the app and run `python manage.py smoke`. Playwright captures actual desktop and mobile UI. No screenshots are synthesized. Refresh the screenshots before rebuilding the deck if UI changes.
