import asyncio
from pathlib import Path

from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

from lairn.common import load_pdf_pages
from lairn.config import LLM, OUTPUT_LANGUAGE
from lairn.curriculum.models import SchoolCurriculumDocumentCharacteristics, CurriculumSummary
from lairn.curriculum.prompts import (
    PT_SUMMARIZE_CURRICULUM_PAGE,
    PT_PARSE_CURRICULUM_STRUCTURE,
    PT_WRITE_SUBJECT_OVERVIEW,
)

from loguru import logger


class CurriculumSummarizer:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or LLM

        self.model = ChatOpenAI(model_name=self.model_name, temperature=0.0)

    async def _analyze_document_structure(
        self, preface_content: str
    ) -> SchoolCurriculumDocumentCharacteristics:
        logger.info("Analyzing document structure")
        # Set up a parser + inject instructions into the prompt template.
        parser = PydanticOutputParser(pydantic_object=SchoolCurriculumDocumentCharacteristics)

        chain = PT_PARSE_CURRICULUM_STRUCTURE | self.model | parser

        return await chain.ainvoke(
            {
                "preface_content": preface_content,
                "response_format": parser.get_format_instructions(),
                "response_language": OUTPUT_LANGUAGE,
            }
        )

    async def _summarize_curriculum_page(
        self, page_number: int, page_content: str, doc_structure: str
    ) -> str:
        prompt = PT_SUMMARIZE_CURRICULUM_PAGE.format(
            doc_structure=doc_structure,
            page_number=page_number,
            page_content=page_content,
            response_language=OUTPUT_LANGUAGE,
        )

        response = await self.model.ainvoke(prompt)
        return response.content

    async def _write_final_overview(self, summary: CurriculumSummary) -> str:
        prompt = PT_WRITE_SUBJECT_OVERVIEW.format(
            subject=summary.subject,
            summary=summary,
            response_language=OUTPUT_LANGUAGE,
        )

        response = await self.model.ainvoke(prompt)
        return response.content

    async def summarize_curriculum_pdf(
        self,
        pdf_path: str | Path,
        n_preface_pages: int = 3,
        page_number_offset: int = 3,
        page_separator: str = "\n\n",
    ) -> str:
        logger.info(f"Summarizing curriculum PDF: {pdf_path}")
        pages = load_pdf_pages(pdf_path)

        preface_content = page_separator.join([page.page_content for page in pages[:n_preface_pages]])
        doc_structure = await self._analyze_document_structure(preface_content)
        doc_structure_fmt = doc_structure.str_format()

        logger.info("Summarizing curriculum pages")

        async def summarize_page(page):
            page_num = page.metadata["page"] + 1 - page_number_offset
            logger.info(f"Treating page {page_num}")
            summary = await self._summarize_curriculum_page(page_num, page.page_content, doc_structure_fmt)
            return dict(page_number=page_num, summary=summary)

        tasks = [summarize_page(page) for page in pages[n_preface_pages:]]
        summaries = await asyncio.gather(*tasks)

        summaries = sorted(summaries, key=lambda x: x["page_number"])
        summaries = CurriculumSummary(
            subject=doc_structure.subject, structure=doc_structure.structure, summaries=summaries
        )

        return await self._write_final_overview(summaries)
