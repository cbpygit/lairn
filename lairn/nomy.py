from datetime import date, timedelta
import re
from pathlib import Path
from typing import List, Optional, Tuple

from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from lairn.config import MAIN_DIR, OUTPUT_LANGUAGE, LLM


NOMY_SUMMARY_PDF_DIR = MAIN_DIR / "nomy" / "summaries"
NOMY_SUMMARY_DATA_DIR = MAIN_DIR / "nomy" / "data"


class NomySubjectActivity(BaseModel):
    subject: str = Field(description="The school subject")
    teacher: str = Field(description="The teacher's name in parentheses")
    activities: List[str] = Field(description="List of activities done in this subject")


class NomyWeekSummary(BaseModel):
    week_number: int = Field(description="The calendar week number")
    year: int = Field(description="The year")
    start_date: date = Field(description="Start date of the week")
    end_date: date = Field(description="End date of the week")
    subjects: List[NomySubjectActivity] = Field(description="List of subject activities")

    def str_fmt(self) -> str:
        result = f"# Week {self.week_number}/{self.year} ({self.start_date} - {self.end_date})\n\n"
        for subject in self.subjects:
            result += f"## {subject.subject} ({subject.teacher})\n"
            for activity in subject.activities:
                result += f"- {activity}\n"
            result += "\n"
        return result


class NomyWeekSummaries(BaseModel):
    """Wrapper model for list of week summaries"""

    summaries: List[NomyWeekSummary] = Field(description="List of weekly summaries")


def get_date_range_for_week(year: int, week: int) -> Tuple[date, date]:
    """Get start and end date for a given year and week number."""
    # Find the first day of the year
    first_day = date(year, 1, 1)

    # Find the Monday of week 1
    monday_week_1 = first_day + timedelta(days=(-first_day.weekday()))
    if first_day.weekday() > 3:  # If Jan 1 is Fri/Sat/Sun, Monday is in week 1 of next year
        monday_week_1 += timedelta(weeks=1)

    # Calculate the Monday of our target week
    target_monday = monday_week_1 + timedelta(weeks=week - 1)
    target_sunday = target_monday + timedelta(days=6)

    return target_monday, target_sunday


def parse_filename_info(filename: str) -> Optional[Tuple[int, List[int]]]:
    """Parse year and week numbers from filename.
    Returns tuple of (year, [week_numbers]) or None if pattern doesn't match.
    """
    # Match patterns like "Wochenberichte_2025_KW_1_2_Stufe_2.pdf"
    # or "Wochenberichte_Stufe_2A_KW_5_6.pdf"
    # or "Wochenberichte_Stufe_2_A_KW_7_9.pdf" (range of weeks)
    pattern = r"Wochenberichte_(\d{4})(?:_Stufe_\w+)?_KW_(\d+)(?:_(\d+))?|Wochenberichte_Stufe_\w+(?:_\w+)?_KW_(\d+)(?:_(\d+))?"

    match = re.search(pattern, filename)
    if not match:
        return None

    # Extract year from either first or fourth group
    year_str = match.group(1)

    # Extract weeks from either groups 2-3 or 4-5
    if year_str:
        # First pattern matched
        year = int(year_str)
        week1 = int(match.group(2))
        week2_str = match.group(3)
    else:
        # Second pattern matched
        # For files without explicit year, use current year
        year = date.today().year
        week1 = int(match.group(4))
        week2_str = match.group(5)

    # If there's a second week number, it could be either:
    # 1. A single additional week (e.g., KW_1_2 means weeks 1 and 2)
    # 2. The end of a range (e.g., KW_7_9 means weeks 7, 8, and 9)
    weeks = [week1]
    if week2_str:
        week2 = int(week2_str)
        if week2 - week1 <= 1:
            # Just add the second week
            weeks.append(week2)
        else:
            # It's a range, add all weeks in between
            weeks.extend(range(week1 + 1, week2 + 1))

    return year, weeks


PT_PARSE_NOMY_WEEK = PromptTemplate(
    template="""
    |SYSTEM|
    
    # Expert school report parser
    
    You are parsing a weekly report from the Nomy School. The report contains activities for different 
    subjects, with the teacher's name in parentheses. Parse this into a structured format.
    
    The report may contain one or more weeks. Each week starts with a header like "KW X | DD.MM.-DD.MM."
    followed by subject sections. Extract all weeks from the report.

    |USER|

    ## Report year and weeks

    Year: {year}
    Week numbers: {weeks}

    ## Weekly report content

    {content}

    ## Response format

    {response_format}

    ## Response language

    {response_language}
    """,
    input_variables=["year", "weeks", "content", "response_format", "response_language"],
)


class NomyReportParser:
    def __init__(self, model_name: str | None = None):
        from langchain_openai import ChatOpenAI

        self.model = ChatOpenAI(
            model_name=model_name or LLM, temperature=1.0 if model_name == "o1-preview" else 0.0
        )

    def parse_pdf(self, pdf_path: Path) -> List[NomyWeekSummary]:
        """Parse a Nomy weekly report PDF and return a list of week summaries."""
        from langchain_core.output_parsers import PydanticOutputParser
        from lairn.common import load_pdf_pages

        # Parse year and weeks from filename
        file_info = parse_filename_info(pdf_path.name)
        if not file_info:
            raise ValueError(f"Could not parse year and week numbers from filename: {pdf_path.name}")

        year, weeks = file_info

        # Load and combine PDF pages
        pages = load_pdf_pages(pdf_path)
        content = "\n\n".join(page.page_content for page in pages)

        # Set up parser
        parser = PydanticOutputParser(pydantic_object=NomyWeekSummaries)

        # Create and run chain
        chain = PT_PARSE_NOMY_WEEK | self.model | parser

        result = chain.invoke(
            {
                "year": year,
                "weeks": weeks,
                "content": content,
                "response_format": parser.get_format_instructions(),
                "response_language": OUTPUT_LANGUAGE,
            }
        )

        # Update each summary with correct dates based on year and week number
        for summary in result.summaries:
            start_date, end_date = get_date_range_for_week(year, summary.week_number)
            summary.year = year
            summary.start_date = start_date
            summary.end_date = end_date

        return result.summaries

    def save_summaries(self, summaries: List[NomyWeekSummary]):
        """Save the parsed summaries as JSON files."""
        NOMY_SUMMARY_DATA_DIR.mkdir(parents=True, exist_ok=True)

        for summary in summaries:
            output_file = NOMY_SUMMARY_DATA_DIR / f"nomy_week_{summary.year}_{summary.week_number:02d}.json"
            output_file.write_text(summary.model_dump_json(indent=2))
