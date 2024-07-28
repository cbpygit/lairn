import asyncio
from pathlib import Path

from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

from lairn.config import LLM, OUTPUT_LANGUAGE
from lairn.curriculum.models import Curriculum
from lairn.curriculum.prompts import PT_CURRICULUM_PARSER

from loguru import logger


class CurriculumParser:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or LLM

        self.model = ChatOpenAI(model_name=self.model_name, temperature=0.0)

    async def parse_curriculum(self, curriculum_summary: str) -> Curriculum:
        logger.info(f"Parsing curriculum {curriculum_summary.splitlines()[0]}")
        # Set up a parser + inject instructions into the prompt template.
        parser = PydanticOutputParser(pydantic_object=Curriculum)

        chain = PT_CURRICULUM_PARSER | self.model | parser

        return await chain.ainvoke(
            {
                "summary": curriculum_summary,
                "response_format": parser.get_format_instructions(),
                "response_language": OUTPUT_LANGUAGE,
            }
        )
