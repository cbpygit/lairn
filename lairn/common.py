from datetime import date
from pathlib import Path

import tiktoken
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from lairn.config import LLM, STUDENT_BIRTH_DATE


def load_pdf_pages(pdf_path: str | Path) -> list[Document]:
    loader = PyPDFLoader(pdf_path)
    return loader.load_and_split()


def count_tokens(text: str, model: str = LLM) -> int:
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(text))
    return num_tokens


def get_student_age_today() -> int:
    today = date.today()
    return (
        today.year
        - STUDENT_BIRTH_DATE.year
        - (
            (today.month, today.day)
            < (
                STUDENT_BIRTH_DATE.month,
                STUDENT_BIRTH_DATE.day,
            )
        )
    )
