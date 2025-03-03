#!/usr/bin/env python3
from datetime import date
import click
from pathlib import Path
from typing import List

from lairn.config import MAIN_DIR
from lairn.reporting.week_summarizer import WeekSummarizer


def process_week(summarizer: WeekSummarizer, year: int, week_number: int, out_dir: Path, force: bool = False):
    """Process a single week and save the summary."""
    start_date = date.fromisocalendar(year, week_number, 1)
    end_date = date.fromisocalendar(year, week_number, 7)

    json_file_name = f"{year}_week_{week_number}_{start_date}-{end_date}.json"
    md_file_name = f"{year}_week_{week_number}_{start_date}-{end_date}.md"

    json_out_path = out_dir / json_file_name
    md_out_path = out_dir / md_file_name

    # Check if summary already exists
    if json_out_path.exists():
        if not force:
            click.echo(
                f"⏭️  Skipping week {year}/{week_number} - summary already exists (use --force to overwrite)"
            )
            return
        else:
            click.echo(f"⚠️  Overwriting existing summary for week {year}/{week_number}")

    click.echo(f"🔄 Processing week {year}/{week_number} ({start_date} to {end_date})")

    try:
        summary = summarizer.summarize_week(start_date, end_date)

        # Save JSON summary
        with open(json_out_path, "w") as f:
            f.write(summary.model_dump_json())

        # Save Markdown summary
        with open(md_out_path, "w") as f:
            md_str = summary.str_fmt()
            if "## Other" in md_str:
                md_str = md_str.replace("## Other", "## Weiteres")
            f.write(md_str)

        click.echo(f"✅ Saved summary for week {year}/{week_number} to {md_out_path}")

    except Exception as e:
        click.echo(f"❌ Error processing week {year}/{week_number}: {str(e)}", err=True)


def get_week_info(offset: int = 0) -> tuple[int, int]:
    """Get year and week number based on current date and offset."""
    year, this_week, _ = date.today().isocalendar()
    target_week = this_week - offset

    # Handle year boundary
    if target_week < 1:
        year -= 1
        # Get the number of weeks in the previous year
        last_day_of_year = date(year, 12, 31)
        _, weeks_in_year, _ = last_day_of_year.isocalendar()
        target_week = weeks_in_year + target_week

    return year, target_week


@click.command()
@click.option(
    "--weeks",
    "-w",
    multiple=True,
    type=int,
    help="Week offset(s) from current week. Can be specified multiple times.",
)
@click.option("--current", "-c", is_flag=True, help="Process current week instead of previous week.")
@click.option("--force", "-f", is_flag=True, help="Force overwrite of existing summaries.")
def main(weeks: List[int], current: bool, force: bool):
    """Generate weekly summaries for homeschooling activities.

    By default, the script will skip weeks that already have summaries.
    Use --force to overwrite existing summaries.

    If no weeks are specified, processes the current week if --current is set,
    otherwise processes the previous week.

    If multiple week offsets are provided, processes all specified weeks.

    # Example usage:
    Process previous week (default)
    >> python scripts/summarize_week.py

    Process current week
    >> python scripts/summarize_week.py --current

    Process weeks from 2 and 3 weeks ago
    >> python scripts/summarize_week.py -w 2 -w 3

    Force regeneration of last week's summary
    >> python scripts/summarize_week.py --force

    """
    out_dir = MAIN_DIR / "weekly_summaries"
    out_dir.mkdir(exist_ok=True, parents=True)

    summarizer = WeekSummarizer()

    if force:
        click.echo("⚠️  Force mode enabled - existing summaries will be overwritten")

    # Determine which weeks to process
    if not weeks:
        # Default: process current week or previous week
        offset = 0 if current else 1
        year, week_number = get_week_info(offset)
        process_week(summarizer, year, week_number, out_dir, force)
    else:
        # Process all specified week offsets
        for offset in weeks:
            year, week_number = get_week_info(offset)
            process_week(summarizer, year, week_number, out_dir, force)

    click.echo("✨ Weekly summary generation complete")


if __name__ == "__main__":
    main()
