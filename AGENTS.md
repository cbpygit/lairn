# Lairn Agent Guide

## Project Overview

`lairn` is a Poetry-managed Python project for homeschool reporting and related learning workflows.
The main recurring workflows are:

- parsing raw learning logs and Sofatutor activity exports
- processing Nomy school PDFs into structured JSON
- generating weekly summaries and merged scans PDFs
- producing helper reports such as activities grouped by subject

## Important Paths

- `lairn/`: application code
- `lairn/reporting/`: weekly summaries and scan handling
- `lairn/integrations/sofatutor/`: Sofatutor parsing and import logic
- `scripts/`: operational entry points used by the project
- `tests/`: pytest coverage for reporting and parsing behavior

## Working Conventions

- Use `poetry run ...` for Python commands.
- Prefer the `Taskfile` for common project tasks once it exists.
- Use conventional commits when creating commits.
- Do not commit secrets or environment files such as `.env`.
- This repo may read and write data outside the workspace via configured paths, so inspect scripts before running commands with side effects.

## Common Workflows

- Weekly summary generation: `scripts/summarize_week.py`
- Scans-only rebuild: `scripts/rebuild_week_scans.py`
- Nomy PDF processing: `scripts/process_nomy_reports.py`
- Sofatutor activity import: `scripts/update_sofatutor_activities.py`
- Activity rollup by subject: `scripts/activities_by_subject.py`

## Testing Guidance

- Run targeted tests for the files you changed when possible.
- For reporting changes, start with:
  - `tests/test_learn_log.py`
  - `tests/test_week_summarizer.py`
  - `tests/test_week_scans.py`
- Run the full test suite before larger commits if the change affects shared code.

## Reporting-Specific Notes

- Weekly summary failures can come from raw log parsing before any LLM call happens.
- Scan collection currently supports `Gescannt_*`, `PXL_*`, and WhatsApp-style `IMG-YYYYMMDD-WAxxxx.*` filenames.
- Scan PDFs are built from both PDFs and images, and may rename Pixel and WhatsApp images during normalization.
- If only the scans PDF needs to be refreshed, prefer the scans-only rebuild script/task over regenerating the text summary.

## Safe Agent Behavior

- Preserve user changes in a dirty worktree.
- Prefer small, targeted fixes over broad refactors.
- When a script writes output files, mention the affected outputs in your final response.
