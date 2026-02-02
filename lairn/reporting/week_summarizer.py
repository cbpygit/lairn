from datetime import date
from typing import Optional

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from lairn.common import create_chat_openai
from lairn.config import (
    LLM_WEEK_PARSE_MODEL,
    LLM_WEEK_PARSE_REASONING_EFFORT,
    LLM_WEEK_REPORT_MODEL,
    LLM_WEEK_REPORT_REASONING_EFFORT,
    MAIN_DIR,
    OUTPUT_LANGUAGE,
)
from lairn.context_mixin import ContextMixinClassLevel2
from lairn.integrations.sofatutor.activity_list_parser import SofatutorLearningActivity
from lairn.learn_log import LearnLogMessage
from lairn.nomy import NOMY_SUMMARY_DATA_DIR, NomyWeekSummary


SUMMARY_DATA_DIR = MAIN_DIR / "weekly_summaries" / "data"


PT_LIST_WEEK_ACTIVITIES = PromptTemplate(
    template="""
    |SYSTEM|

    # Expert home schooling learning assistant

    You receive a list of homeschooling activities of a single student with age {age} logged during the week.
    List the week's activities in a clear and readable format. Group the activities by
    school subject, using only the known subjects from the list provided in the user instructions. If the
    activity is not related to a school subject, group it under the "Other" category. Not all subjects need
    to be present in the logs.
    
    Take into account the following context information for common terms and tools to know what they mean
    when they appear in the logs:
    
    {additional_explanations}

    |USER|

    ## Logs for the week

    {logs}

    ## Known subjects

    {known_subjects}

    ## Further instructions
      - Only provide responses for subjects that really occur in the logs
      - Stick close to the actual logs, making only edits to improve readability and to give 
        a standardized format
      - Do not make anything up
      - Do NOT include dates or timestamps in the activity descriptions
      - Each activity should be a simple bullet point without date prefixes

    ## Response format

    {response_format}

    ## Response language

    {response_language}

""",
    input_variables=[
        "age",
        "additional_explanations",
        "logs",
        "known_subjects",
        "response_format",
        "response_language",
    ],
)


PT_SUMMARIZE_WEEK = PromptTemplate(
    template="""
    |SYSTEM|

    # Expert home schooling learning assistant

    You receive a list of homeschooling activities of a single student with age {age} logged during the week,
    and possibly activities from their regular school (Nomy School). Write a short summary to explain what 
    progress the student made during the week. The summary should be concise but informative. The target 
    reader is an external instructor who monitors the student's progress and uses this to give advice to 
    the parents.
    
    Take into account the following context information for common terms and tools to know what they mean
    when they appear in the logs:
    
    {additional_explanations}

    ## Previous summaries

    {previous_summaries}

    |USER|

    ## Homeschooling Activities

    {activities}

    ## Nomy School Activities This Week

    {nomy_activities}

    ## Additional Context

    {additional_context}

    ## Further instructions
      - If additional context is provided above, take it fully into account when writing the summary.
        This may include special circumstances (illness, vacation, first week after break, etc.) that
        should be naturally integrated into the narrative.
      - Start directly with substantive content about what the student learned or worked on this week.
        Do NOT begin with meta-commentary about the week's organization, data availability, or generic
        statements like "Die Woche war überwiegend häuslich organisiert" or "Diese Woche kombinierte...".
        Instead, begin with the most important learning content.
      - If Nomy School data is not available (indicated by "No Nomy School data available"), do NOT
        mention this fact at all. Do not say the report is missing, delayed, or will be added later.
        Simply write the summary based on the homeschooling activities alone.
      - If Nomy School data IS available, naturally integrate it with the homeschooling activities,
        showing how they complement each other.
      - If the notes contain information about skipped Nomy school attendance, take it into account.
      - Take into account the previous summaries to avoid repeating yourself, and to achieve a
        "good flow" for a reader who reads multiple week summaries in a row. Vary your phrasing and
        sentence structure to avoid monotonous patterns.
      - In general: Respond with an unstructured (or minimally structured if too long) text summary 
        (may use paragraphs, but not sections, bullet points or lists). Exception: if the notes
        describe a project or other out-of-the-ordinary activities of longer duration, you should
        use sections and make it stand out.
      - Do not judge or evaluate the activities, just summarize them.
      - Do not list the activities again, except to give examples. You should rather describe general 
        categories and the progress that was made. Be concise.
      - Do not mention exact time durations of activities.
      - Make sure major activities are emphasized over small details.
      - Do not speculate about what might have happened at Nomy School if no data is provided.

    ## Response language

    {response_language}

""",
    input_variables=[
        "age",
        "additional_explanations",
        "previous_summaries",
        "activities",
        "nomy_activities",
        "additional_context",
        "response_language",
    ],
)


# 1) Add a new prompt for summarizing a single subject
PT_NOMY_SUBJECT_SUMMARY = PromptTemplate(
    template="""
    |SYSTEM|
    
    # Expert summarizer for Nomy School subject
    
    You are given a subject name, the teacher, and a list of activities. Summarize them into a concise 
    sentence or two, but do not mention the teacher's name in your response. The final response should be
    in the language specified. Do not list every bullet in detail—just present a short narrative overview.
    Any references to the teacher must be omitted.

    |USER|

    ## Subject
    {subject_name}

    ## Teacher
    {teacher}

    ## Activities
    {activities}

    ## Response language
    {response_language}
    """,
    input_variables=["subject_name", "teacher", "activities", "response_language"],
)


class WeekSubjectActivities(BaseModel):
    subject: str = Field(description="The school subject")
    activities: list[str] = Field(description="The activities of the week for this subject")


class WeekActivities(BaseModel):
    activities: list[WeekSubjectActivities] = Field(
        description="The learning activities of the week per subject"
    )

    def str_fmt(self) -> str:
        formatted_activities = ""
        for subject_activity in self.activities:
            formatted_activities += f"## {subject_activity.subject}\n"
            for sub_activity in subject_activity.activities:
                formatted_activities += f"  - {sub_activity}\n"
            formatted_activities += "\n"
        return formatted_activities


class WeekActivitiesWithDateInfo(BaseModel):
    week_number: int = Field(description="The week number")
    year: int = Field(description="The year")
    start_date: date = Field(description="The start date of the week")
    end_date: date = Field(description="The end date of the week")
    summary: str = Field(description="The summary of the week's activities")
    activities: list[WeekSubjectActivities] = Field(
        description="The learning activities of the week per subject"
    )
    nomy_activities: Optional[str] = Field(
        description="Summary of Nomy School activities this week", default=None
    )
    is_preliminary: bool = Field(
        description="Whether this is a preliminary version due to missing Nomy reports", default=False
    )

    def str_fmt(self) -> str:
        formatted_activities = ""
        for subject_activity in self.activities:
            formatted_activities += f"## {subject_activity.subject}\n"
            for sub_activity in subject_activity.activities:
                formatted_activities += f"  - {sub_activity}\n"
            formatted_activities += "\n"

        title_suffix = " (Vorversion)" if self.is_preliminary else ""

        # Only include Nomy section if there are actual activities
        nomy_section = ""
        if self.nomy_activities:
            nomy_section = f"\n## Nomy School\n{self.nomy_activities}\n\n"

        return f"""
# {self.year}/{self.week_number} ({self.start_date} - {self.end_date}){title_suffix}

{self.summary}

{nomy_section}{formatted_activities}
"""


class WeekSummarizer(ContextMixinClassLevel2):
    def __init__(
        self,
        model_name: str | None = None,
        parse_model: str | None = None,
        parse_reasoning_effort: str | None = None,
        report_model: str | None = None,
        report_reasoning_effort: str | None = None,
        n_previous_summaries: int = 3,
    ):
        # Legacy support: if model_name is provided, use it for both
        if model_name:
            self.parse_model = create_chat_openai(
                model_name=model_name,
                temperature=1.0 if model_name.startswith("o") else 1.0,
            )
            self.report_model = self.parse_model
        else:
            # Use separate models for parsing and reporting
            self.parse_model = create_chat_openai(
                model_name=parse_model or LLM_WEEK_PARSE_MODEL,
                temperature=1.0,
                reasoning_effort=parse_reasoning_effort or LLM_WEEK_PARSE_REASONING_EFFORT,
            )
            self.report_model = create_chat_openai(
                model_name=report_model or LLM_WEEK_REPORT_MODEL,
                temperature=1.0,
                reasoning_effort=report_reasoning_effort or LLM_WEEK_REPORT_REASONING_EFFORT,
            )
        
        print(f"Parse model: {self.parse_model}")
        print(f"Report model: {self.report_model}")
        self.additional_explanations = self.load_additional_explanations()
        self.n_previous_summaries = n_previous_summaries

    def get_logs_for_date_range(self, start_date: date, end_date: date) -> list[LearnLogMessage]:
        logs = self.load_logs()
        return [log for log in logs if start_date <= log.timestamp.date() <= end_date]

    def get_sofa_activities_for_date_range(
        self, start_date: date, end_date: date
    ) -> list[SofatutorLearningActivity]:
        logs = self.load_sofa_activities()
        return [log for log in logs if start_date <= log.date_ref <= end_date]

    def get_nomy_activities_for_date_range(
        self, start_date: date, end_date: date
    ) -> Optional[NomyWeekSummary]:
        """Get Nomy school activities for the given week."""
        week_number = start_date.isocalendar()[1]
        year = start_date.year
        nomy_file = NOMY_SUMMARY_DATA_DIR / f"nomy_week_{year}_{week_number:02d}.json"

        if not nomy_file.exists():
            return None

        return NomyWeekSummary.model_validate_json(nomy_file.read_text())

    def summarize_nomy_subject_items(self, subject_name: str, teacher: str, bullet_points: list[str]) -> str:
        """
        Use an LLM prompt to get a short textual summary of the bullet points for one Nomy subject.
        """
        subject_activities_text = "\n".join(f"- {bp}" for bp in bullet_points)

        chain = PT_NOMY_SUBJECT_SUMMARY | self.parse_model
        resp = chain.invoke(
            {
                "subject_name": subject_name,
                "teacher": teacher,
                "activities": subject_activities_text,
                "response_language": OUTPUT_LANGUAGE,
            }
        )
        return resp.content.strip()

    def format_nomy_activities(self, nomy_summary: Optional[NomyWeekSummary]) -> str:
        """Format Nomy activities with a concise subject-wise summary."""
        if not nomy_summary:
            return ""  # Return empty string instead of "No Nomy School activities recorded for this week"

        lines = []
        for subj in nomy_summary.subjects:
            short_summary = self.summarize_nomy_subject_items(
                subject_name=subj.subject,
                teacher=subj.teacher,
                bullet_points=subj.activities,
            )
            lines.append(f"- **{subj.subject}**: {short_summary}")

        return "\n" + "\n".join(lines)

    def load_previous_summaries(self) -> str:
        all_summaries = [
            WeekActivitiesWithDateInfo.model_validate_json(f.read_text())
            for f in SUMMARY_DATA_DIR.glob("*.json")
        ]
        sorted_summaries = sorted(all_summaries, key=lambda x: x.start_date, reverse=True)[
            : self.n_previous_summaries
        ]

        # Return only the narrative summaries (not the full markdown with bullet lists)
        # to reduce repetitive phrasing
        return "\n\n---\n\n".join([
            f"Week {s.week_number}/{s.year} ({s.start_date} - {s.end_date}):\n{s.summary}"
            for s in sorted_summaries
        ])

    def summarize_week(self, start_date: date, end_date: date, comment: str | None = None) -> WeekActivitiesWithDateInfo:
        print(f"Summarizing week from {start_date} to {end_date}")

        iso_cal = start_date.isocalendar()
        assert iso_cal[2] == 1, "Start date must be a Monday"
        assert end_date.isocalendar()[2] == 7, "End date must be a Sunday"

        week_number = iso_cal[1]
        assert week_number == end_date.isocalendar()[1], "Start and end date must be in the same week"
        year = iso_cal[0]

        logs = self.get_logs_for_date_range(start_date, end_date)
        sofa_activities = self.get_sofa_activities_for_date_range(start_date, end_date)
        logs = logs + sofa_activities
        if len(logs) == 0:
            raise ValueError("No logs found for the given date range")

        # Get Nomy activities for the week
        nomy_summary = self.get_nomy_activities_for_date_range(start_date, end_date)
        nomy_activities = self.format_nomy_activities(nomy_summary)
        is_preliminary = nomy_summary is None

        # Set up a parser + inject instructions into the prompt template.
        parser = PydanticOutputParser(pydantic_object=WeekActivities)

        chain = PT_LIST_WEEK_ACTIVITIES | self.parse_model | parser

        activities = chain.invoke(
            {
                "age": self.student_age,
                "additional_explanations": self.additional_explanations,
                "logs": "".join([log.str_fmt() for log in logs]),
                "known_subjects": str(list(sorted(self.load_curricula().keys()))),
                "response_format": parser.get_format_instructions(),
                "response_language": OUTPUT_LANGUAGE,
            }
        )

        # Prepare additional context (comment if provided)
        additional_context = comment if comment else "No additional context provided."
        
        summary = self.report_model.invoke(
            PT_SUMMARIZE_WEEK.template.format(
                age=self.student_age,
                additional_explanations=self.additional_explanations,
                previous_summaries=self.load_previous_summaries(),
                activities=activities.str_fmt(),
                nomy_activities=nomy_activities or "No Nomy School data available for this week.",
                additional_context=additional_context,
                response_language=OUTPUT_LANGUAGE,
            )
        ).content

        return WeekActivitiesWithDateInfo(
            week_number=week_number,
            year=year,
            start_date=start_date,
            end_date=end_date,
            summary=summary,
            activities=activities.activities,
            nomy_activities=nomy_activities,
            is_preliminary=is_preliminary,
        )
