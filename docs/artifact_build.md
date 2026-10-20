# Rebuilding submission artifacts

`python -m scripts.build_figures` regenerates the sample synthetic FHIR document, architecture PDF and measured evaluation figure using reportlab. The editable flow is also in architecture.mmd. Run evaluation first when the model/data change.

The submitted presentation is the retained PDF at
`presentation/project_presentation.pdf`. The previous editable PPTX was
removed at the team's request. The app itself does not require presentation
authoring tools.

The deck's quantitative chart uses actual reports/metrics.json values and an embedded editable workbook. Source notes accompany every slide. Validation checks package integrity, geometry, fonts and native chart data, then imports the final package with the authoring tool. It has not been opened in native PowerPoint in this environment.

The PDF is the competition submission artifact supplied by the team. If a
future editable source is created, inspect the regenerated PDF before
replacing this file.

Screenshots: launch the app and run `python manage.py smoke`. Playwright captures actual desktop and mobile UI. No screenshots are synthesized. Refresh the screenshots before rebuilding the deck if UI changes.
