from datetime import date
from pathlib import Path

import tiktoken
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

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


def create_chat_openai(
    model_name: str,
    temperature: float = 1.0,
    reasoning_effort: str | None = None,
) -> ChatOpenAI:
    """
    Create a ChatOpenAI instance with optional reasoning effort parameter.
    
    This helper handles version compatibility for reasoning_effort parameter
    which is used by reasoning models like o1/o3/gpt-5.2.
    
    Args:
        model_name: The model name (e.g., "gpt-5.2", "gpt-4o")
        temperature: Temperature setting (default 1.0)
        reasoning_effort: Reasoning effort level ("low", "medium", "high") for reasoning models
    
    Returns:
        ChatOpenAI instance configured with the specified parameters
    """
    kwargs = {
        "model": model_name,
        "temperature": temperature,
    }
    
    # Add reasoning_effort if specified
    if reasoning_effort is not None:
        # Try to pass it directly first (newer API versions)
        try:
            return ChatOpenAI(reasoning_effort=reasoning_effort, **kwargs)
        except TypeError:
            # Fall back to model_kwargs for older versions
            kwargs["model_kwargs"] = {"reasoning_effort": reasoning_effort}
            return ChatOpenAI(**kwargs)
    
    return ChatOpenAI(**kwargs)
