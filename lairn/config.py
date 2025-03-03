import os
from datetime import date
from dateutil import parser
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", None)
LLM = os.environ.get("LLM", "gpt-4o-mini")
OUTPUT_LANGUAGE = os.environ.get("OUTPUT_LANGUAGE", "de")
MAIN_DIR = Path(os.environ.get("MAIN_DIR"))

STUDENT_BIRTH_DATE = os.environ.get("STUDENT_BIRTH_DATE", None)
assert STUDENT_BIRTH_DATE is not None, "Please set STUDENT_BIRTH_DATE in .env file."
STUDENT_BIRTH_DATE = parser.parse(STUDENT_BIRTH_DATE).date()
