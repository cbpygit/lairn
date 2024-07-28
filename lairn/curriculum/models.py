from pydantic import BaseModel, Field


class SchoolCurriculumDocumentSection(BaseModel):
    title: str = Field(description="The title of the section")


class SchoolCurriculumDocumentCharacteristics(BaseModel):
    subject: str = Field(description="The school subject the document is about")
    structure: list[SchoolCurriculumDocumentSection] = Field(description="The structure of the document")

    def str_format(self) -> str:
        """Formats the structure as:

        Subject: {subject}
        TOC:
          - {section1}
          - {section2}
          ...

        """
        s = f"Subject: {self.subject}\nTOC:\n"
        s += "\n".join([f"  - {section.title}" for section in self.structure])
        return s


class CurriculumSummary(BaseModel):
    subject: str = Field(description="The school subject the document is about")
    structure: list[SchoolCurriculumDocumentSection] = Field(description="The structure of the document")
    summaries: list[dict] = Field(description="The summaries of the curriculum pages")

    def str_format(self) -> str:
        toc = "\n".join([f"  - {section.title}" for section in self.structure])
        summaries = "\n\n".join(
            [f"## {summary['page_number']}:\n{summary['summary']}" for summary in self.summaries]
        )
        return f"""
# {self.subject}

{toc}

{summaries}
"""

        s = f"Subject: {self.subject}\nTOC:\n"
        s += "\n".join([f"  - {section.title}" for section in self.structure])
        return s


class CurriculumSection(BaseModel):
    title: str = Field(description="The title of the section")
    learning_targets: list[str] = Field(description="The learning targets of the section")


class Curriculum(BaseModel):
    subject: str = Field(description="The school subject the document is about")
    grades: list[int] = Field(description="The grades the curriculum is for")
    sections: list[CurriculumSection] = Field(description="The sections of the curriculum")

    @property
    def grades_formatted(self) -> str:
        return f"{min(self.grades)} - {max(self.grades)}"

    def str_format(self, section_subset: list[str] | None = None) -> str:
        if isinstance(section_subset, str):
            section_subset = [section_subset]

        s = f"#{self.subject} ({self.grades_formatted})\n"
        for sec in self.sections:
            if section_subset is not None and sec.title not in section_subset:
                continue
            s += f"\n## {sec.title}\n"
            s += "\n".join([f"  - {lt}" for lt in sec.learning_targets])
            s += "\n"
        return s


class LearningTargetExamples(BaseModel):
    section: str = Field(description="The section of the curriculum")
    learning_target: str = Field(description="The learning target")
    examples: list[str] = Field(
        description="Examples for learning and exercising activities that can be "
        "done in the home schooling context to achieve the learning target"
    )
