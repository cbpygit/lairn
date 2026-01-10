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
SCANS_DIR = Path(os.environ.get("SCANS_DIR")) if os.environ.get("SCANS_DIR") else None

# Weekly report model configuration
LLM_WEEK_PARSE_MODEL = os.environ.get("LLM_WEEK_PARSE_MODEL", "gpt-5.2")
LLM_WEEK_PARSE_REASONING_EFFORT = os.environ.get("LLM_WEEK_PARSE_REASONING_EFFORT", "low")
LLM_WEEK_REPORT_MODEL = os.environ.get("LLM_WEEK_REPORT_MODEL", "gpt-5.2")
LLM_WEEK_REPORT_REASONING_EFFORT = os.environ.get("LLM_WEEK_REPORT_REASONING_EFFORT", "high")

STUDENT_BIRTH_DATE = os.environ.get("STUDENT_BIRTH_DATE", None)
assert STUDENT_BIRTH_DATE is not None, "Please set STUDENT_BIRTH_DATE in .env file."
STUDENT_BIRTH_DATE = parser.parse(STUDENT_BIRTH_DATE).date()
