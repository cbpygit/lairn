import os
from functools import lru_cache
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
ACTIVITIES_OUTPUT_DIR = SOFA_DIR / "activities"

DF_SOFA = pd.read_excel(PARSED_DIR / "sofatutor_videos.xlsx")

# Example usage
file_path = SOFA_DIR / "sofatutor_exports" / "20240729_export" / "Mein Sofa.html"
activities = parse_html_file(file_path)


@lru_cache
def find_video_row(url: str) -> Tuple[int, pd.Series]:
    rows = DF_SOFA[DF_SOFA.url.str.contains(url)]
    related_years = rows.year.unique()
    return related_years, rows.iloc[0]


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
                        "description": video_details["description"],
                    }
                )

            out_path = ACTIVITIES_OUTPUT_DIR / activity_parsed.default_file_name
            if os.path.isfile(out_path) and SKIP_EXISTING:
                continue

            out_path.write_text(activity_parsed.json())


if __name__ == "__main__":
    main()
