from datetime import date

from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from lairn.config import LLM, OUTPUT_LANGUAGE
from lairn.context_mixin import ContextMixinClassLevel2

from lairn.learn_log import LearnLogMessage

PT_LIST_WEEK_ACTIVITIES = PromptTemplate(
    template="""
    |SYSTEM|

    # Expert home schooling learning assistant

    You receive a list of homeschooling activities of a single student with age {age} logged during the week.
    List the week's activities in a clear and readable format. Group the activities by
    school subject, using only the known subjects from the list provided in the user instructions. If the
    activity is not related to a school subject, group it under the "Other" category. Not all subjects need
    to be present in the logs.

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

    ## Response format

    {response_format}

    ## Response language

    {response_language}

""",
    input_variables=[
        "age",
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

    You receive a list of homeschooling activities of a single student with age {age} logged during the week.
    Write a short summary to explain what progress the student made during the week. The summary should be
    concise but informative. The target reader is an external instructor who monitors the student's progress
    and uses this to give advice to the parents. 

    |USER|

    ## Activities

    {activities}

    ## Further instructions
      - Respond with an unstructured text summary (no sections, paragraphs, bullet points or lists)
      - Do not judge or evaluate the activities, just summarize them
      - Do not list the activities again, except to give examples. You should rather describe general 
        categories and the progress that was made. Be concise.

    ## Response language

    {response_language}

""",
    input_variables=[
        "age",
        "activities",
        "response_language",
    ],
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

    def str_fmt(self) -> str:
        formatted_activities = ""
        for subject_activity in self.activities:
            formatted_activities += f"## {subject_activity.subject}\n"
            for sub_activity in subject_activity.activities:
                formatted_activities += f"  - {sub_activity}\n"
            formatted_activities += "\n"
        return f"""
# {self.year}/{self.week_number} ({self.start_date} - {self.end_date})

{self.summary}

{formatted_activities}
"""


class WeekSummarizer(ContextMixinClassLevel2):
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or LLM

        self.model = ChatOpenAI(model_name=self.model_name, temperature=0.0)

    def get_logs_for_date_range(self, start_date: date, end_date: date) -> list[LearnLogMessage]:
        logs = self.load_logs()
        return [log for log in logs if start_date <= log.timestamp.date() <= end_date]

    def summarize_week(self, start_date: date, end_date: date) -> WeekActivitiesWithDateInfo:
        iso_cal = start_date.isocalendar()
        assert iso_cal[2] == 1, "Start date must be a Monday"
        assert end_date.isocalendar()[2] == 7, "End date must be a Sunday"

        week_number = iso_cal[1]
        assert week_number == end_date.isocalendar()[1], "Start and end date must be in the same week"
        year = iso_cal[0]

        logs = self.get_logs_for_date_range(start_date, end_date)
        if len(logs) == 0:
            raise ValueError("No logs found for the given date range")

        # Set up a parser + inject instructions into the prompt template.
        parser = PydanticOutputParser(pydantic_object=WeekActivities)

        chain = PT_LIST_WEEK_ACTIVITIES | self.model | parser

        activities = chain.invoke(
            {
                "age": self.student_age,
                "logs": "".join([log.str_fmt() for log in logs]),
                "known_subjects": str(list(sorted(self.load_curricula().keys()))),
                "response_format": parser.get_format_instructions(),
                "response_language": OUTPUT_LANGUAGE,
            }
        )

        summary = self.model.invoke(
            PT_SUMMARIZE_WEEK.template.format(
                age=self.student_age,
                activities=activities.str_fmt(),
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
        )
