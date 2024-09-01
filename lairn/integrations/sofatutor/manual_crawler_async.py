# import asyncio
# import json
# import os.path
# from pathlib import Path
# from time import sleep
# from typing import Literal
#
# import aiohttp
# import pandas as pd
# import requests
# import unmarkd
# from bs4 import BeautifulSoup
# from loguru import logger
#
# from lairn.integrations.sofatutor import SOFA_DIR
#
# SOFATUTOR_URL = "https://www.sofatutor.com"
#
# YEAR_TYPE_DICT_DE = {
#     "grade": "klasse",
#     "learn_year": "lernjahr",
# }
#
# IS_GRADE_SYSTEM = {
#     "Mathematik": True,
#     "Deutsch": True,
#     "Englisch": False,
#     "Biologie": True,
#     "Physik": True,
#     "Chemie": True,
#     "Französisch": False,
#     "Latein": False,
#     "Spanisch": False,
#     "Geschichte": True,
#     "Geographie": True,
#     "Sachunterricht": True,
#     "Musik": True,
#     "Lern- und Arbeitstechniken": True,
# }
#
# PARSE_SUBJECTS = [
#     "Mathematik",
#     "Deutsch",
#     "Biologie",
#     "Physik",
#     "Chemie",
#     # "Geschichte",
#     # "Geographie",
#     "Sachunterricht",
#     "Musik",
#     # "Lern- und Arbeitstechniken",
#     "Englisch",
# ]
#
# AVAILABLE_GRADES = {
#     "Mathematik": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
#     "Deutsch": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
#     "Englisch": [1, 2, 3, 4, 5, 6, 7],
#     "Biologie": [5, 6, 7, 8, 9, 10, 11, 12, 13],
#     "Physik": [5, 6, 7, 8, 9, 10, 11, 12, 13],
#     "Chemie": [6, 7, 8, 9, 10, 11, 12, 13],
#     "Geschichte": [5, 6, 7, 8, 9, 10, 11, 12, 13],
#     "Geographie": [5, 6, 7, 8, 9, 10, 11, 12, 13],
#     "Sachunterricht": [1, 2, 3, 4],
#     "Musik": [5, 6, 7, 8, 9, 10, 11, 12, 13],
#     "Lern- und Arbeitstechniken": [5, 6, 7, 8, 9, 10, 11, 12, 13],
# }
#
#
# def get_cookie(subject: str, year: int, year_type: Literal["grade", "learn_year"]) -> dict:
#     return {"_sofatutor_subject_level": f"{YEAR_TYPE_DICT_DE[year_type]}-{year}-{subject}"}
#
#
# async def _get_soup(
#     session: aiohttp.ClientSession, url: str, cookie: dict | None = None
# ) -> BeautifulSoup | None:
#     headers = {"User-Agent": "Mozilla/5.0"}  # Add more headers if needed
#
#     async with session.get(url, cookies=cookie, headers=headers) as response:
#         if response.status != 200:
#             return None
#         text = await response.text()
#         return BeautifulSoup(text, "html.parser")
#
#
# def _get_content_structure_header(soup: BeautifulSoup) -> str | None:
#     for section in soup.find_all("section", class_="content-structure-header"):
#         return section.find_next("h1").text
#     return None
#
#
# def _get_content_structure_text(soup: BeautifulSoup) -> str | None:
#     for section in soup.find_all("section", class_="content-structure-text"):
#         if "Themenübersicht" in section.text:
#             return unmarkd.unmark(section.text)
#     return None
#
#
# def _iter_topics(soup: BeautifulSoup) -> tuple[str, str]:
#     for section in soup.find_all("section", class_="content-structure-topics"):
#         for li in section.find_all("li"):
#             a = li.find_next("a")
#             yield a["href"], a["data-tracking-label"]
#
#
# def _clean_description(desc: str) -> str:
#     if "Noch nicht angemeldet?" in desc:
#         desc = desc.split("Noch nicht angemeldet?")[0].strip()
#     if "Schülerinnen und Schüler haben bereits unsere Übungen absolviert." in desc:
#         lines = desc.splitlines()
#         for i, line in enumerate(lines):
#             if "Schülerinnen und Schüler haben bereits unsere Übungen absolviert." in line:
#                 break
#         desc = "\n".join(lines[:i]).strip()
#     return desc
#
#
# async def _parse_video_page(session: aiohttp.ClientSession, url: str) -> dict:
#     logger.info(f"Processing video page {url}")
#     soup = await _get_soup(session, url)
#
#     title = None
#     description = None
#     transcript = None
#     try:
#         title = soup.find_all("a", class_="videos-accordion__title")[0].find_next("b").text.strip()
#     except:
#         pass
#     try:
#         description = unmarkd.unmark(soup.find_all("div", class_="videos-accordion__content")[0].text).strip()
#         description = _clean_description(description)
#     except:
#         pass
#     try:
#         transcript = unmarkd.unmark(
#             soup.find_all("div", class_="videos-transcript-accordion__inner")[0].text
#         ).strip()
#     except:
#         pass
#
#     return {
#         "video_url": url,
#         "title": title,
#         "description": description,
#         "transcript": transcript,
#     }
#
#
# async def walk_lowest_level_topic_page(session: aiohttp.ClientSession, soup: BeautifulSoup) -> dict | None:
#     topic = _get_content_structure_header(soup)
#     if topic is None:
#         return None
#
#     topic_description = None
#     for section in soup.find_all("section", class_="content-topic-description"):
#         topic_description = unmarkd.unmark(section.text)
#         break
#
#     video_tasks = []
#     video_lists = soup.find_all("ul", class_="list-video-meta")
#     assert len(video_lists) == 1
#     video_list = video_lists[0]
#     for li in video_list.find_all("li"):
#         a = li.find_next("a")
#         href = a["href"]
#         video_url = f"{SOFATUTOR_URL}{href}"
#         video_tasks.append(_parse_video_page(session, video_url))
#
#     videos = await asyncio.gather(*video_tasks)
#
#     return {"topic": topic, "topic_description": topic_description, "videos": videos}
#
#
# async def walk_topics(session: aiohttp.ClientSession, topic_href: str, cookie: dict) -> dict | None:
#     logger.info(
#         f"Processing {topic_href} with cookie {cookie['_sofatutor_subject_level'] if cookie else None}"
#     )
#     url = f"{SOFATUTOR_URL}{topic_href}"
#     soup = await _get_soup(session, url, cookie)
#
#     if soup is None:
#         return None
#
#     topic = _get_content_structure_header(soup)
#     if topic is None:
#         return None
#
#     content_structure_text = _get_content_structure_text(soup)
#
#     sub_topics_tasks = []
#     for sub_topic_url, label in _iter_topics(soup):
#         sub_topics_tasks.append(asyncio.create_task(walk_topics(session, sub_topic_url, cookie)))
#
#     sub_topics = await asyncio.gather(*sub_topics_tasks)
#
#     if not sub_topics:
#         assert content_structure_text is None
#         return {
#             "href": topic_href,
#             "url": url,
#             "cookie": cookie,
#             "topic": topic,
#             "video_content": await walk_lowest_level_topic_page(session, soup),
#         }
#
#     return {
#         "href": topic_href,
#         "url": url,
#         "cookie": cookie,
#         "topic": topic,
#         "content_structure_text": content_structure_text,
#         "sub_topics": [
#             {"label": label[1], "content": sub_topic}
#             for label, sub_topic in zip(_iter_topics(soup), sub_topics)
#         ],
#     }
#
#
# class SofatutorCrawler:
#     def __init__(self):
#         pass
#
#     @staticmethod
#     def get_sub_url(subject: str, grade: int | None = None, learn_year: int | None = None) -> str:
#         if grade is None and learn_year is None:
#             raise ValueError("Either grade or learn_year must be provided")
#         elif grade is None:
#             assert learn_year is not None
#             return f"{SOFATUTOR_URL}{subject}/lernjahr-{learn_year}"
#         elif learn_year is None:
#             assert grade is not None
#             return f"{SOFATUTOR_URL}{subject}/klasse-{grade}"
#         else:
#             raise ValueError("Only one of grade or learn_year must be provided")
#
#     def get_subjects(self) -> list[dict]:
#         response = requests.get(SOFATUTOR_URL)
#
#         if response.status_code == 200:
#             webpage_content = response.text
#         else:
#             print("Failed to retrieve the webpage")
#             exit()
#
#         soup = BeautifulSoup(webpage_content, "html.parser")
#
#         subjects = []
#         ul = soup.find_all("ul", class_="subject-cards-list")[0]
#         for li in ul.find_all("li"):
#             href = li.find_next("a")["href"]
#             subject = li.find_next("span").text
#             subjects.append({"url": href, "subject": subject})
#
#         return subjects
#
#     async def parse_sub_url(self, sub_url: str, cookie=dict) -> dict | None:
#         response = requests.get(sub_url + "?ref=videos")
#
#         if not response.status_code == 200:
#             return None
#
#         soup = BeautifulSoup(response.text, "html.parser")
#
#         topic_overview = None
#         for section in soup.find_all("section", class_="content-structure-text"):
#             if "Themenübersicht" in section.text:
#                 topic_overview = unmarkd.unmark(section.text)
#         parsed = dict(topic_overview=topic_overview)
#
#         topics_section = None
#         for section in soup.find_all("section", class_="content-structure-topics"):
#             if "Themenbereiche" in section.text:
#                 topics_section = section
#
#         if topics_section is None:
#             logger.warning(f"No topics found for {sub_url}")
#             return parsed
#
#         topics_content = []
#         for li in topics_section.find_all("li"):
#             topic_href = li.find_next("a")["href"]
#             topic_url = f"{SOFATUTOR_URL}{topic_href}"
#             try:
#                 async with aiohttp.ClientSession() as session:
#                     topic_content = await walk_topics(session, topic_href, cookie)
#                 topics_content.append(topic_content)
#             except Exception as e:
#                 logger.exception(f"Failed to process topic {topic_url}")
#                 continue
#         parsed["topics"] = topics_content
#
#         return parsed
#
#     async def crawl(self):
#         subjects = self.get_subjects()
#
#         for subject in subjects:
#             subject_str_ = subject["subject"]
#             if not subject_str_ in PARSE_SUBJECTS:
#                 continue
#
#             grades = AVAILABLE_GRADES[subject_str_]
#             is_grade_system = IS_GRADE_SYSTEM[subject_str_]
#
#             subject_code = subject["url"].split("/")[-1]
#
#             if is_grade_system:
#                 for grade in grades:
#                     json_name = (
#                         SOFA_DIR / "sofatutor_parsed" / "details" / f"{subject['subject']}-{grade}.json"
#                     )
#                     if os.path.isfile(json_name):
#                         logger.info(f"Skipping {json_name}")
#                         continue
#
#                     sub_url = self.get_sub_url(subject["url"], grade=grade)
#                     cookie = get_cookie(subject_code, grade, year_type="grade")
#
#                     content = await self.parse_sub_url(sub_url, cookie)
#
#                     if content is not None:
#                         content["year"] = grade
#                         content["year_type"] = "grade"
#                         content["subject"] = subject["subject"]
#
#                         with open(json_name, "w") as f:
#                             logger.info(f"Writing to {f.name}")
#                             f.write(json.dumps(content))
#
#             else:
#                 for learn_year in grades:
#                     json_name = (
#                         SOFA_DIR / "sofatutor_parsed" / "details" / f"{subject['subject']}-{learn_year}.json"
#                     )
#                     if os.path.isfile(json_name):
#                         logger.info(f"Skipping {json_name}")
#                         continue
#
#                     sub_url = self.get_sub_url(subject["url"], learn_year=learn_year)
#                     cookie = get_cookie(subject_code, learn_year, year_type="learn_year")
#
#                     content = await self.parse_sub_url(sub_url, cookie)
#
#                     if content is not None:
#                         content["year"] = learn_year
#                         content["year_type"] = "learn_year"
#                         content["subject"] = subject["subject"]
#
#                         with open(json_name, "w") as f:
#                             logger.info(f"Writing to {f.name}")
#                             f.write(json.dumps(content))
#
#
# def walk_videos(struct: dict, topic_chain: tuple | None = None) -> list[dict] | pd.DataFrame:
#     videos = []
#     if "video_content" in struct:
#         for video in struct["video_content"]["videos"]:
#             videos.append(
#                 dict(
#                     url=video["url"],
#                     topic_chain=topic_chain,
#                     title=video["content"]["title"],
#                     description=video["content"]["description"],
#                 )
#             )
#     if "sub_topics" in struct:
#         for sub_topic in struct["sub_topics"]:
#             videos.extend(walk_videos(sub_topic["content"], topic_chain + (sub_topic["label"],)))
#     if "topics" in struct:
#         for topic in struct["topics"]:
#             videos.extend(walk_videos(topic, (topic["topic"],)))
#
#         df = pd.DataFrame(videos)
#         df["subject"] = struct["subject"]
#         df["year_type"] = struct["year_type"]
#         df["year"] = struct["year"] if "year" in struct else struct["grade"]
#         return df.loc[:, ["subject", "year_type", "year", "topic_chain", "title", "url", "description"]]
#
#     return videos
#
#
# async def crawl_sofatutor():
#     crawler = SofatutorCrawler()
#     await crawler.crawl()
#
#
# def extract_videos():
#     dfs = []
#     path = SOFA_DIR / "sofatutor_parsed" / "details"
#
#     for jpath in path.glob("*.json"):
#         with open(jpath) as f:
#             d = json.load(f)
#         df = walk_videos(d)
#         dfs.append(df)
#
#     df = pd.concat(dfs)
#     df.to_excel(SOFA_DIR / "sofatutor_parsed" / "sofatutor_videos.xlsx", index=False)
#
#
# if __name__ == "__main__":
#     asyncio.run(crawl_sofatutor())
#     # extract_videos()
