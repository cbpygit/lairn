import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Tuple

import pandas as pd
from loguru import logger

from lairn.integrations.sofatutor import SOFA_DIR
from lairn.integrations.sofatutor.activity_list_parser import parse_html_file, SofatutorLearningActivity

SKIP_EXISTING = True
TEST_STR = "?launchpad=test"
SOFAHELD_STR = "practice_app"
EXPORTS_DIR = SOFA_DIR / "sofatutor_exports"
PARSED_DIR = SOFA_DIR / "sofatutor_parsed"
ACTIVITIES_OUTPUT_DIR = Path("/home/carlo/private/lairn/tmp/")

DF_SOFA = pd.read_excel(PARSED_DIR / "sofatutor_videos.xlsx")

# Example usage
file_path = SOFA_DIR / "sofatutor_exports" / "20240729_export" / "Mein Sofa.html"
activities = parse_html_file(file_path)


@lru_cache
def find_video_row(url: str) -> Tuple[int, pd.Series]:
    rows = DF_SOFA[DF_SOFA.url.str.contains(url)]
    related_years = rows.year.unique()
    return related_years, rows.iloc[0]


def clean_string(input_string):
    cleaned_string = re.sub(r"\n+", "\n", input_string)
    cleaned_string = re.sub(r"\s+", " ", cleaned_string)

    # Replace escaped quotation marks with slanted quotation marks
    cleaned_string = cleaned_string.replace('"', "“")

    # Replace newline characters with " | "
    cleaned_string = cleaned_string.replace("\n", " | ")

    # Remove any redundant sentence starting with "Teste dein Wissen"
    cleaned_string = re.sub(r"\s*\|*\s*Teste dein Wissen.*?(\.|!|\?)", "", cleaned_string)

    # Remove leading or trailing whitespace and extra separators
    cleaned_string = cleaned_string.strip().strip("|")

    return cleaned_string


def main():
    for export_dir in EXPORTS_DIR.glob("*export*"):
        if not os.path.isdir(export_dir):
            continue

        if not "Mein Sofa.html" in os.listdir(export_dir):
            continue

        export = export_dir / "Mein Sofa.html"
        logger.info("Parsing {}", export)

        activities = parse_html_file(export)
        for data in activities:
            url = data["url"].strip()

            if (
                not url
                == "https://www.sofatutor.com/englisch/videos/prepositions-die-praepositionen?launchpad=test"
            ):
                continue

            if SOFAHELD_STR in url:
                activity_parsed = SofatutorLearningActivity.model_validate(
                    {
                        **data,
                        "activity_type": "practice",
                        "related_years": None,
                        "year_type": None,
                        "topic_chain": None,
                        "description": None,
                    }
                )
            else:
                is_test = TEST_STR in url
                related_years, video_details = find_video_row(url.replace(TEST_STR, ""))

                activity_parsed = SofatutorLearningActivity.model_validate(
                    {
                        **data,
                        "activity_type": "test" if is_test else "video",
                        "related_years": related_years,
                        "year_type": video_details["year_type"],
                        "topic_chain": video_details["topic_chain"],
                        "description": clean_string(video_details["description"]),
                    }
                )

            out_path = ACTIVITIES_OUTPUT_DIR / activity_parsed.default_file_name
            if os.path.isfile(out_path) and SKIP_EXISTING:
                continue

            out_path.write_text(activity_parsed.json())

            break
        break


if __name__ == "__main__":
    main()
