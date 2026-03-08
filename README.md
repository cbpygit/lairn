# lairn

AI-assisted learning workflows for homeschool reporting.

## Setup

This project uses Poetry for dependency management.

```bash
poetry install
```

For common operations, prefer the `Taskfile`:

```bash
task --list
```

## Common Tasks

Run the full test suite:

```bash
task test
```

Run the reporting-focused tests:

```bash
task test-reporting
```

Generate the current week's summary:

```bash
task summarize-current
```

Regenerate the current week's summary:

```bash
task summarize-current-force
```

Generate the current week's summary with additional context:

```bash
task summarize-current COMMENT="Student was sick this week"
```

## Scans-Only Rebuild

If the weekly text summary is already correct and only the scans PDF needs to be refreshed, use the dedicated scans rebuild workflow.

Rebuild the current week's scans PDF:

```bash
task rebuild-scans-current-force
```

Rebuild the previous week's scans PDF:

```bash
task rebuild-scans-previous-force
```

Rebuild a week by offset from the current week:

```bash
task rebuild-scans-week OFFSET=2 EXTRA_ARGS="--force"
```

You can also run the script directly:

```bash
poetry run python scripts/rebuild_week_scans.py --current --force
```

## Other Workflows

Process Nomy PDF reports:

```bash
task process-nomy
```

Parse Sofatutor exports into activity JSON:

```bash
task update-sofatutor
```

Build an activity report grouped by subject:

```bash
task activities-by-subject START=2026-01-01 END=2026-01-31
```

## Notes

- Weekly scans support `Gescannt_*`, Pixel `PXL_*`, and WhatsApp `IMG-YYYYMMDD-WAxxxx.*` filenames.
- Pixel and WhatsApp images are normalized into `Gescannt_*` filenames during scan PDF rebuilds.
