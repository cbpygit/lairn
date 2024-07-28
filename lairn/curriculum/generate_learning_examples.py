import asyncio

from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

from lairn.config import LLM, OUTPUT_LANGUAGE
from lairn.curriculum.models import LearningTargetExamples, Curriculum
from lairn.curriculum.prompts import PT_GENERATE_LEARNING_EXAMPLES

from loguru import logger


class LearningExampleGenerator:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or LLM

        self.model = ChatOpenAI(model_name=self.model_name, temperature=0.0)

    async def _generate_examples_for_single_target(
        self, curriculum: Curriculum, section: str, learning_target: str, num_examples: int
    ) -> LearningTargetExamples:
        logger.info(f"Handling learning target: {learning_target} of section: {section}")
        # Set up a parser + inject instructions into the prompt template.
        parser = PydanticOutputParser(pydantic_object=LearningTargetExamples)

        chain = PT_GENERATE_LEARNING_EXAMPLES | self.model | parser

        examples = await chain.ainvoke(
            {
                "grades": curriculum.grades_formatted,
                "subject": curriculum.subject,
                "num_examples": num_examples,
                "curriculum": curriculum.str_format(section_subset=section),
                "section": section,
                "learning_target": learning_target,
                "response_format": parser.get_format_instructions(),
                "response_language": OUTPUT_LANGUAGE,
            }
        )
        return examples

    async def create_examples(
        self, curriculum: Curriculum, num_examples: int = 5
    ) -> list[LearningTargetExamples]:
        logger.info(f"Generating learning examples for curriculum with subject {curriculum.subject}")

        tasks = []
        for section in curriculum.sections:
            logger.info(f"Handling section: {section.title}")
            for learning_target in section.learning_targets:
                task = self._generate_examples_for_single_target(
                    curriculum, section.title, learning_target, num_examples
                )
                tasks.append(task)

        return await asyncio.gather(*tasks)
