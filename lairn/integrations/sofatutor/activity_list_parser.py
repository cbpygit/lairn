import os
from datetime import date
from functools import lru_cache
from pathlib import Path

import requests
from dateutil import parser
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from slugify import slugify


# Replace German month names with English equivalents
translations = {
    "Januar": "January",
    "Februar": "February",
    "März": "March",
    "April": "April",
    "Mai": "May",
    "Juni": "June",
    "Juli": "July",
    "August": "August",
    "September": "September",
    "Oktober": "October",
    "November": "November",
    "Dezember": "December",
}


def translate_date_string(date_string: str) -> str:
    for de, en in translations.items():
        date_string = date_string.replace(de, en)

    # Remove the weekday to avoid parsing issues
    date_string = " ".join(date_string.split(", ")[1:])
    return date_string


def parse_date_string(date_string: str) -> date:
    return parser.parse(translate_date_string(date_string), dayfirst=True).date()


@lru_cache
def parse_video_description(url: str) -> dict:
    response = requests.get(url)

    if response.status_code == 200:
        webpage_content = response.text
    else:
        print("Failed to retrieve the webpage")
        exit()

    soup = BeautifulSoup(webpage_content, "html.parser")

    title = None
    description = None
    transcript = None
    try:
        title = soup.find_all("a", class_="videos-accordion__title")[0].find_next("h2").find_next("b").text
    except:
        pass
    try:
        description = soup.find_all("div", class_="videos-accordion__content")[0].find_next("p").text
    except:
        pass
    try:
        transcript = (
            soup.find_all("div", class_="videos-transcript-accordion__inner")[0]
            .find_next("div", class_="markdown latex-processing-active")
            .text
        )
    except:
        pass

    return {"title": title, "description": description, "transcript": transcript}


def parse_activity_list_item(item) -> dict:
    activity_dict = {}

    # Extract the URL
    activity_dict["url"] = item.find_next("a")["href"]

    # Extract the school subject label
    subject_label_div = item.find("div", class_="acccount-activity-item__subject-label")
    if subject_label_div and subject_label_div.span:
        activity_dict["subject_label"] = subject_label_div.span.text
    else:
        activity_dict["subject_label"] = None

    # Extract the title
    title_div = item.find("div", class_="h3 acccount-activity-item__title")
    if title_div and title_div.b:
        activity_dict["title"] = title_div.b.text
    else:
        activity_dict["title"] = None

    # Count the number of checkmarks
    checkmarks = item.find_all("i", class_="content-item-state-icon--complete")
    if len(checkmarks) == 0:
        checkmarks = ["yellow" in li.attrs["class"] for li in item.find_all("i", class_="icon--star")]

    tasks = item.find_all("i", class_="content-item-state-icon")
    activity_dict["total_tasks"] = len(tasks)
    activity_dict["tasks_completed"] = len(checkmarks)

    return activity_dict


def parse_html_file(file_path: Path) -> list[dict]:
    with open(file_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, "html.parser")

    activity_list_containers = soup.find_all("div", class_="account-activity-list-item-container")

    activities = []
    for container in activity_list_containers:
        date_ref = parse_date_string(container.find_next("div").text)
        for item in container.find_all("ul"):
            d_parsed = parse_activity_list_item(item)

            if (
                d_parsed["url"] == "https://jobs.sofatutor.com/ueber-uns"
                or d_parsed["tasks_completed"] == 0
                or d_parsed["subject_label"] is None
            ):
                continue

            d_parsed["date_ref"] = date_ref
            activities.append(d_parsed)

    return activities


class SofatutorLearningActivity(BaseModel):
    date_ref: date = Field(description="The date of the activity")
    subject_label: str = Field(description="The school subject the activity relates to")
    title: str = Field(description="The title of the specific learning content video or exercise")
    activity_type: str = Field(description="Type of the activity, either video, test or practice")
    total_tasks: int = Field(description="The total number of tasks in the activity")
    tasks_completed: int = Field(description="The number of tasks completed in the activity")
    url: str = Field(description="The URL of the activity")
    related_years: list[int] | None = Field(description="The school years the activity is related to")
    year_type: str | None = Field(
        description="The type of school year the activity is related to, either grade or learning year"
    )
    topic_chain: str | None = Field(description="The chain of categories the content is filed under")
    description: str | None = Field(description="The description of the video content")

    @classmethod
    def from_json_file(cls, file_path: Path) -> "SofatutorLearningActivity":
        with open(file_path, "r", encoding="utf-8") as f:
            return cls.model_validate(f.read())

    @property
    def default_file_name(self) -> str:
        title_simple = slugify(self.title)
        return f"{self.date_ref}_{self.subject_label}_{title_simple}_{self.activity_type}.json"

    def str_fmt(self, with_url: bool = False) -> str:
        url_str = f"\n  - URL: {self.url}\n" if with_url else ""
        return f"""
### Sofatutor Learning Activity

#### General Properties
  - Date: {self.date_ref}
  - Subject: {self.subject_label}
  - Title: {self.title}
  - Activity type: {self.activity_type}
  - Score: {self.tasks_completed}/{self.total_tasks}
  - Categorization: {self.year_type} {self.related_years} - {self.topic_chain}{url_str}
  
#### Description
{self.description}
  
"""
