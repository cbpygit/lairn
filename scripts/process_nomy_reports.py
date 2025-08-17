import asyncio
from pathlib import Path

from loguru import logger

from lairn.nomy import NomyReportParser, NOMY_SUMMARY_PDF_DIR, NOMY_SUMMARY_DATA_DIR, parse_filename_info


async def process_nomy_reports():
    """Process all Nomy report PDFs and create JSON summaries."""
    parser = NomyReportParser()

    # Create output directory if it doesn't exist
    NOMY_SUMMARY_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Get list of already processed weeks
    existing_files = set(NOMY_SUMMARY_DATA_DIR.glob("nomy_week_*.json"))
    processed_weeks = set()

    for file in existing_files:
        # Extract year and week from filename (format: nomy_week_YYYY_WW.json)
        parts = file.stem.split("_")
        if len(parts) == 4:
            try:
                year = int(parts[2])
                week = int(parts[3])
                processed_weeks.add((year, week))
            except (ValueError, IndexError):
                logger.warning(f"Could not parse year and week from {file}")

    # Process each PDF file
    for pdf_path in NOMY_SUMMARY_PDF_DIR.glob("*.pdf"):
        logger.info(f"Checking {pdf_path}")

        # Parse year and weeks from filename
        file_info = parse_filename_info(pdf_path.name)
        if not file_info:
            logger.warning(f"Could not parse year and week numbers from filename: {pdf_path.name}")
            continue

        year, weeks = file_info

        # Check if all weeks from this PDF have already been processed
        all_weeks_processed = all((year, week) in processed_weeks for week in weeks)

        if all_weeks_processed:
            logger.info(f"Skipping {pdf_path} - all weeks already processed")
            continue

        # Process the PDF
        logger.info(f"Processing {pdf_path}")
        try:
            summaries = parser.parse_pdf(pdf_path)
            parser.save_summaries(summaries)

            # Update processed weeks
            for summary in summaries:
                logger.info(f"Adding {summary.year} {summary.week_number} to processed weeks")
                processed_weeks.add((summary.year, summary.week_number))

            logger.info(f"Successfully processed {pdf_path}")
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {str(e)}")


async def main():
    """Main function with retry logic for rate limits."""
    import openai

    while True:
        try:
            await process_nomy_reports()
            break
        except openai.RateLimitError:
            logger.warning("Rate limit reached, waiting 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
