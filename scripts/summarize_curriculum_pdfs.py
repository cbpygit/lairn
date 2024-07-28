import asyncio
import os

import openai

from lairn.config import MAIN_DIR
from lairn.curriculum.summarize_curriculum import CurriculumSummarizer


async def main():
    # Create an instance of CurriculumSummarizer
    summarizer = CurriculumSummarizer()

    # Hard-coded PDF path (make sure this path is correct on your system)
    pdfs_path = MAIN_DIR / "Schullehrplan_Grundschule"

    for pdf_path in pdfs_path.glob("*.pdf"):
        out_path = os.path.join("tmp_output", pdf_path.name.replace(".pdf", ".txt"))
        if os.path.isfile(out_path):
            continue

        result = await summarizer.summarize_curriculum_pdf(pdf_path)
        with open(out_path, "w") as f:
            f.write(result)


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
