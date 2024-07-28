import asyncio
import os

import openai

from lairn.config import MAIN_DIR
from lairn.curriculum.curriculum_parser import CurriculumParser


async def main():
    # Create an instance of CurriculumSummarizer
    parser = CurriculumParser()

    # Hard-coded PDF path (make sure this path is correct on your system)
    summary_path = MAIN_DIR / "Schullehrplan_Grundschule_Zusammenfassungen" / "Schuljahre 1-2"

    for summary_path in summary_path.glob("*.txt"):
        out_path = summary_path.parent / "pydantic" / summary_path.name
        out_path = out_path.with_suffix(".json")
        if os.path.isfile(out_path):
            continue

        with open(summary_path, "r") as f:
            summary = f.read()

        curriculum = await parser.parse_curriculum(summary)
        out_path.write_text(curriculum.json())


async def main_safe():
    """Same as main, but waits 5seconds and retries in case of
    openai.RateLimitError"""
    while True:
        try:
            await main()
            break
        except openai.RateLimitError:
            print("Rate limit error, waiting 5 seconds")
            await asyncio.sleep(5)


# Run the main function using asyncio
if __name__ == "__main__":
    asyncio.run(main_safe())
