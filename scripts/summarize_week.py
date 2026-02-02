#!/usr/bin/env python3
from datetime import date
import click
from pathlib import Path
from typing import List

from lairn.config import MAIN_DIR, LLM, SCANS_DIR
from lairn.reporting.week_summarizer import WeekSummarizer
from lairn.reporting.week_scans import build_week_scans_pdf


def process_week(summarizer: WeekSummarizer, year: int, week_number: int, out_dir: Path, data_dir: Path, force: bool = False, comment: str | None = None):
    """Process a single week and save the summary."""
    start_date = date.fromisocalendar(year, week_number, 1)
    end_date = date.fromisocalendar(year, week_number, 7)

    json_file_name = f"{year}_week_{week_number}_{start_date}-{end_date}.json"
    md_file_name = f"{year}_week_{week_number}_{start_date}-{end_date}.md"

    json_out_path = data_dir / json_file_name
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
    if comment:
        click.echo(f"📝 With comment: {comment}")

    try:
        summary = summarizer.summarize_week(start_date, end_date, comment=comment)

        # Save JSON summary to data directory
        with open(json_out_path, "w") as f:
            f.write(summary.model_dump_json())

        # Save Markdown summary to main directory
        with open(md_out_path, "w") as f:
            md_str = summary.str_fmt()
            if "## Other" in md_str:
                md_str = md_str.replace("## Other", "## Weiteres")
            f.write(md_str)

        click.echo(f"✅ Saved summary for week {year}/{week_number}")
        click.echo(f"   JSON: {json_out_path}")
        click.echo(f"   MD:   {md_out_path}")
        
        # Generate scans PDF if SCANS_DIR is configured
        if SCANS_DIR:
            scans_pdf_name = f"{year}_week_{week_number}_{start_date}-{end_date}_scans.pdf"
            scans_pdf_path = out_dir / scans_pdf_name
            
            click.echo(f"🔄 Building scans PDF for week {year}/{week_number}...")
            try:
                success = build_week_scans_pdf(
                    scans_dir=SCANS_DIR,
                    start_date=start_date,
                    end_date=end_date,
                    output_path=scans_pdf_path,
                    normalize_pixel=True,
                    compress=True
                )
                if success:
                    click.echo(f"✅ Saved scans PDF: {scans_pdf_path}")
                else:
                    click.echo(f"⚠️  No scans found for week {year}/{week_number}")
            except Exception as e:
                click.echo(f"❌ Error building scans PDF: {str(e)}", err=True)
        else:
            click.echo("ℹ️  SCANS_DIR not configured, skipping scans PDF generation")

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
@click.option(
    "--comment",
    "-m",
    type=str,
    help="Additional context or comment to include in the report (e.g., 'Student was sick this week').",
)
def main(weeks: List[int], current: bool, force: bool, comment: str):
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

    Process current week with context comment
    >> python scripts/summarize_week.py --current --comment "Levy was sick this week"

    Process weeks from 2 and 3 weeks ago
    >> python scripts/summarize_week.py -w 2 -w 3

    Force regeneration of last week's summary with comment
    >> python scripts/summarize_week.py --force -m "First week after winter break, includes activities from break"

    """
    out_dir = MAIN_DIR / "weekly_summaries"
    data_dir = out_dir / "data"
    out_dir.mkdir(exist_ok=True, parents=True)
    data_dir.mkdir(exist_ok=True, parents=True)

    summarizer = WeekSummarizer()

    if force:
        click.echo("⚠️  Force mode enabled - existing summaries will be overwritten")

    # Determine which weeks to process
    if not weeks:
        # Default: process current week or previous week
        offset = 0 if current else 1
        year, week_number = get_week_info(offset)
        process_week(summarizer, year, week_number, out_dir, data_dir, force, comment)
    else:
        # Process all specified week offsets
        for offset in weeks:
            year, week_number = get_week_info(offset)
            process_week(summarizer, year, week_number, out_dir, data_dir, force, comment)

    click.echo("✨ Weekly summary generation complete")


if __name__ == "__main__":
    main()
