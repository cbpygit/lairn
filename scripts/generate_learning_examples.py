import asyncio
import json
import os

import openai

from lairn.config import MAIN_DIR
from lairn.curriculum.generate_learning_examples import LearningExampleGenerator
from lairn.curriculum.load import load_curricula
from lairn.curriculum.models import LearningTargetExamples


def results_to_markdown_string(subject: str, results: list[LearningTargetExamples]) -> str:
    md_str = f"# {subject}\n\n"
    section = ""
    for res in results:
        if res.section != section:
            md_str += f"\n## {res.section}\n\n"
            section = res.section

        md_str += f"\n### {res.learning_target}\n\n"
        for example in res.examples:
            md_str += f"  - {example}\n"
    return md_str


async def main():
    # Create an instance of CurriculumSummarizer
    generator = LearningExampleGenerator()

    curricula_path = MAIN_DIR / "Schullehrplan_Grundschule_Zusammenfassungen" / "Schuljahre 1-2" / "pydantic"
    curricula = load_curricula(curricula_path)

    for subject, curriculum in curricula.items():
        out_path = (
            MAIN_DIR
            / "Schullehrplan_Grundschule_Zusammenfassungen"
            / "Schuljahre 1-2"
            / "Beispiele"
            / f"{subject}.md"
        )
        if os.path.isfile(out_path):
            continue

        results = await generator.create_examples(
            curriculum=curriculum,
            num_examples=5,
        )

        md = results_to_markdown_string(subject, results)

        with open(out_path, "w") as f:
            f.write(md)


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
