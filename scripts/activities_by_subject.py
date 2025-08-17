#!/usr/bin/env python3
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple
import click
from collections import defaultdict

from lairn.reporting.week_summarizer import WeekActivitiesWithDateInfo
from lairn.nomy import NomyWeekSummary


def load_weekly_summaries(
    data_dir: Path, start_date: date, end_date: date
) -> List[WeekActivitiesWithDateInfo]:
    """Load all weekly summaries within the given date range."""
    summaries = []

    for json_file in data_dir.glob("*.json"):
        try:
            with open(json_file, "r") as f:
                summary = WeekActivitiesWithDateInfo.model_validate_json(f.read())

            # Check if this week overlaps with our date range
            if summary.end_date >= start_date and summary.start_date <= end_date:
                summaries.append(summary)
        except Exception as e:
            click.echo(f"Error loading {json_file}: {e}", err=True)

    # Sort by start date
    summaries.sort(key=lambda x: x.start_date)
    return summaries


def load_nomy_summaries(nomy_dir: Path, start_date: date, end_date: date) -> List[NomyWeekSummary]:
    """Load all Nomy weekly summaries within the given date range."""
    summaries = []

    for json_file in nomy_dir.glob("*.json"):
        try:
            with open(json_file, "r") as f:
                summary = NomyWeekSummary.model_validate_json(f.read())

            # Check if this week overlaps with our date range
            if summary.end_date >= start_date and summary.start_date <= end_date:
                summaries.append(summary)
        except Exception as e:
            click.echo(f"Error loading Nomy file {json_file}: {e}", err=True)

    # Sort by start date
    summaries.sort(key=lambda x: x.start_date)
    return summaries


def group_activities_by_subject(
    summaries: List[WeekActivitiesWithDateInfo], nomy_summaries: List[NomyWeekSummary]
) -> Dict[str, List[Tuple[date, str, str]]]:
    """Group all activities by subject across all weeks.
    Returns dict with subject as key and list of (date, activity, source) tuples."""
    subject_activities = defaultdict(list)

    # Process homeschooling activities
    for summary in summaries:
        for subject_activity in summary.activities:
            subject = subject_activity.subject
            for activity in subject_activity.activities:
                # Store with the week's start date and source indicator
                subject_activities[subject].append((summary.start_date, activity, "Homeschooling"))

    # Process Nomy School activities
    for nomy_summary in nomy_summaries:
        for subject_data in nomy_summary.subjects:
            subject = subject_data.subject
            for activity in subject_data.activities:
                # Store with the week's start date and source indicator
                subject_activities[subject].append((nomy_summary.start_date, activity, "Nomy School"))

    return dict(subject_activities)


def write_markdown_report(
    subject_activities: Dict[str, List[Tuple[date, str, str]]],
    start_date: date,
    end_date: date,
    output_path: Path,
    include_source: bool = True,
):
    """Write the grouped activities to a markdown file."""
    with open(output_path, "w") as f:
        f.write(f"# Aktivitäten nach Fach\n\n")
        f.write(f"**Zeitraum:** {start_date} bis {end_date}\n\n")

        # Sort subjects alphabetically
        sorted_subjects = sorted(subject_activities.keys())

        for subject in sorted_subjects:
            f.write(f"## {subject}\n\n")

            activities = subject_activities[subject]
            # Sort activities by date
            activities.sort(key=lambda x: x[0])

            for week_start, activity, source in activities:
                if include_source:
                    f.write(f"- **{week_start} ({source}):** {activity}\n")
                else:
                    f.write(f"- **{week_start}:** {activity}\n")

            f.write("\n")


@click.command()
@click.option(
    "--start-date",
    "-s",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    required=True,
    help="Start date in YYYY-MM-DD format",
)
@click.option(
    "--end-date",
    "-e",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    required=True,
    help="End date in YYYY-MM-DD format",
)
@click.option(
    "--data-dir",
    "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="/mnt/c/Users/crlob/Google Drive (private)/Lairn/weekly_summaries/data",
    help="Directory containing weekly summary JSON files",
)
@click.option(
    "--nomy-dir",
    "-n",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="/mnt/c/Users/crlob/Google Drive (private)/Lairn/nomy/data",
    help="Directory containing Nomy School JSON files",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output markdown file path (default: activities_by_subject_YYYY-MM-DD_to_YYYY-MM-DD.md)",
)
@click.option(
    "--no-source", is_flag=True, help="Don't include source (Homeschooling/Nomy School) in the output"
)
def main(start_date, end_date, data_dir: Path, nomy_dir: Path, output: Path, no_source: bool):
    """Generate a markdown report of all activities grouped by subject for a given date range.

    This includes both homeschooling activities and Nomy School activities.

    Example usage:

    Process activities from January 2024:
    >> python scripts/activities_by_subject.py -s 2024-01-01 -e 2024-01-31

    Process activities with custom output:
    >> python scripts/activities_by_subject.py -s 2024-01-01 -e 2024-01-31 -o january_report.md

    Process without source labels:
    >> python scripts/activities_by_subject.py -s 2024-01-01 -e 2024-01-31 --no-source
    """
    # Convert datetime objects to date objects
    start_date = start_date.date()
    end_date = end_date.date()

    # Default output filename if not specified
    if not output:
        output = Path(f"activities_by_subject_{start_date}_to_{end_date}.md")

    click.echo(f"📚 Loading weekly summaries from {data_dir}")
    click.echo(f"🏫 Loading Nomy summaries from {nomy_dir}")
    click.echo(f"📅 Date range: {start_date} to {end_date}")

    # Load summaries
    summaries = load_weekly_summaries(data_dir, start_date, end_date)
    click.echo(f"✅ Loaded {len(summaries)} homeschooling weekly summaries")

    # Load Nomy summaries
    nomy_summaries = load_nomy_summaries(nomy_dir, start_date, end_date)
    click.echo(f"✅ Loaded {len(nomy_summaries)} Nomy School weekly summaries")

    if not summaries and not nomy_summaries:
        click.echo("❌ No summaries found in the specified date range", err=True)
        return

    # Group activities by subject
    subject_activities = group_activities_by_subject(summaries, nomy_summaries)
    click.echo(f"📊 Found activities for {len(subject_activities)} subjects")

    # Write report
    write_markdown_report(subject_activities, start_date, end_date, output, include_source=not no_source)
    click.echo(f"✅ Report written to {output}")

    # Print summary
    click.echo("\n📋 Subject summary:")
    for subject in sorted(subject_activities.keys()):
        activities = subject_activities[subject]
        homeschool_count = sum(1 for _, _, source in activities if source == "Homeschooling")
        nomy_count = sum(1 for _, _, source in activities if source == "Nomy School")
        click.echo(
            f"  - {subject}: {len(activities)} activities (Homeschooling: {homeschool_count}, Nomy: {nomy_count})"
        )


if __name__ == "__main__":
    main()
