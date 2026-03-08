#!/usr/bin/env python3
from datetime import date
from pathlib import Path
from typing import List

import click

from lairn.config import MAIN_DIR, SCANS_DIR
from lairn.reporting.week_scans import build_week_scans_pdf


def rebuild_scans_for_week(year: int, week_number: int, out_dir: Path, force: bool = False) -> None:
    """Rebuild the scans PDF for a single week."""
    if not SCANS_DIR:
        click.echo("❌ SCANS_DIR not configured, cannot build scans PDFs", err=True)
        return

    start_date = date.fromisocalendar(year, week_number, 1)
    end_date = date.fromisocalendar(year, week_number, 7)
    scans_pdf_name = f"{year}_week_{week_number}_{start_date}-{end_date}_scans.pdf"
    scans_pdf_path = out_dir / scans_pdf_name

    if scans_pdf_path.exists() and not force:
        click.echo(
            f"⏭️  Skipping scans PDF for week {year}/{week_number} "
            f"- file already exists (use --force to overwrite)"
        )
        return

    click.echo(f"🔄 Building scans PDF for week {year}/{week_number} ({start_date} to {end_date})")

    try:
        success = build_week_scans_pdf(
            scans_dir=SCANS_DIR,
            start_date=start_date,
            end_date=end_date,
            output_path=scans_pdf_path,
            normalize_pixel=True,
            compress=True,
        )
        if success:
            click.echo(f"✅ Saved scans PDF: {scans_pdf_path}")
        else:
            click.echo(f"⚠️  No scans found for week {year}/{week_number}")
    except Exception as e:
        click.echo(f"❌ Error building scans PDF for week {year}/{week_number}: {str(e)}", err=True)


def get_week_info(offset: int = 0) -> tuple[int, int]:
    """Get year and ISO week number based on today's date and offset."""
    year, this_week, _ = date.today().isocalendar()
    target_week = this_week - offset

    if target_week < 1:
        year -= 1
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
@click.option("--force", "-f", is_flag=True, help="Force overwrite of existing scans PDFs.")
def main(weeks: List[int], current: bool, force: bool) -> None:
    """Rebuild scans PDFs without regenerating weekly text summaries."""
    out_dir = MAIN_DIR / "weekly_summaries"
    out_dir.mkdir(exist_ok=True, parents=True)

    if force:
        click.echo("⚠️  Force mode enabled - existing scans PDFs will be overwritten")

    if not weeks:
        offset = 0 if current else 1
        year, week_number = get_week_info(offset)
        rebuild_scans_for_week(year, week_number, out_dir, force)
    else:
        for offset in weeks:
            year, week_number = get_week_info(offset)
            rebuild_scans_for_week(year, week_number, out_dir, force)

    click.echo("✨ Scans PDF rebuild complete")


if __name__ == "__main__":
    main()
