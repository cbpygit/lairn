import traceback
from datetime import date

from lairn.config import MAIN_DIR
from lairn.reporting.week_summarizer import WeekSummarizer


def main(use_this_week=False):
    out_dir = MAIN_DIR / "weekly_summaries"
    summarizer = WeekSummarizer()

    year, this_week, _ = date.today().isocalendar()

    # for i in range(2, 5):
    i = 4
    last_week = this_week - i

    if last_week < 1:
        year -= 1
        last_week = 52 + last_week

    target_week = this_week if use_this_week else last_week

    start_date = date.fromisocalendar(year, target_week, 1)
    end_date = date.fromisocalendar(year, target_week, 7)
    json_file_name = f"{year}_week_{target_week}_{start_date}-{end_date}.json"
    md_file_name = f"{year}_week_{target_week}_{start_date}-{end_date}.md"

    try:
        json_out_path = out_dir / json_file_name
        if json_out_path.exists():
            raise FileExistsError(f"File {json_out_path} already exists")

        summary = summarizer.summarize_week(start_date, end_date)

        with open(json_out_path, "w") as f:
            f.write(summary.json())
        with open(out_dir / md_file_name, "w") as f:
            md_str = summary.str_fmt()
            if "## Other" in md_str:
                md_str = md_str.replace("## Other", "## Weiteres")
            f.write(md_str)
    except Exception as e:
        print(f"Error summarizing week {target_week}:\n {traceback.format_exc()}\n\n")


if __name__ == "__main__":
    main(False)
