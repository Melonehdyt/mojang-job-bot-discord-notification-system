import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Set
import json
import os
import re


@dataclass
class Job:
    title: str
    location: str
    url: str
    department: str = ""
    posted: str = ""
    source: str = ""

    @property
    def id(self) -> str:
        return f"{self.title}|{self.location}".strip().lower()

    def matches_keywords(self, keywords: List[str]) -> bool:
        if not keywords:
            return True
        text = f"{self.title} {self.department} {self.location}".lower()
        return any(kw.lower() in text for kw in keywords)


class JobTracker:
    def __init__(self, seen_file: str = "seen_jobs.json"):
        self.seen_file = seen_file
        self.seen: Set[str] = self._load_seen()

    def _load_seen(self) -> Set[str]:
        if os.path.exists(self.seen_file):
            with open(self.seen_file, "r") as f:
                return set(json.load(f))
        return set()

    def _save_seen(self):
        with open(self.seen_file, "w") as f:
            json.dump(list(self.seen), f)

    def is_new(self, job: Job) -> bool:
        return job.id not in self.seen

    def mark_seen(self, job: Job):
        self.seen.add(job.id)
        self._save_seen()


class MojangScraper:
    GREENHOUSE_PAGE = "https://boards.greenhouse.io/mojangab"
    HUBMUB_PAGE = "https://www.hubmub.com/company/46675/mojang-studios"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def fetch_greenhouse(self) -> List[Job]:
        jobs = []
        try:
            resp = self.session.get(self.GREENHOUSE_PAGE, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for a in soup.select("a"):
                href = a.get("href", "")
                if "/jobs/" not in href:
                    continue

                title = a.get_text(strip=True)
                if not title or title in ("View Job Details", "Jobs", "Create a Job Alert"):
                    continue

                url = href if href.startswith("http") else f"https://boards.greenhouse.io{href}"

                location = "Stockholm, Sweden"
                parent = a.parent
                if parent:
                    text = parent.get_text()
                    loc_match = re.search(r'(Stockholm|Redmond|Remote|Sweden|USA|US)', text)
                    if loc_match:
                        location = loc_match.group(0)

                jobs.append(Job(
                    title=title,
                    location=location,
                    url=url,
                    source="greenhouse"
                ))
        except Exception as e:
            print(f"[Scraper] Greenhouse error: {e}")
        return jobs

    def fetch_hubmub(self) -> List[Job]:
        jobs = []
        try:
            resp = self.session.get(self.HUBMUB_PAGE, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for a in soup.select("a"):
                href = a.get("href", "")
                if "/jobs/" not in href:
                    continue

                text = a.get_text(strip=True)
                if text != "View Job Details":
                    continue

                # Find title in parent element
                parent = a.parent
                if not parent:
                    continue

                title = ""
                for el in parent.find_all(["h2", "h3", "h4", "strong", "span"]):
                    el_text = el.get_text(strip=True)
                    if el_text and el_text != "View Job Details" and len(el_text) > 3:
                        title = el_text
                        break

                if not title:
                    continue

                url = href if href.startswith("http") else f"https://www.hubmub.com{href}"

                location = "Stockholm, Sweden"
                parent_text = parent.get_text()
                loc_match = re.search(r'(Stockholm|Redmond|Remote|Sweden|USA|US)', parent_text)
                if loc_match:
                    location = loc_match.group(0)

                jobs.append(Job(
                    title=title,
                    location=location,
                    url=url,
                    source="hubmub"
                ))
        except Exception as e:
            print(f"[Scraper] HubMub error: {e}")
        return jobs

    def fetch_all(self) -> List[Job]:
        all_jobs = self.fetch_greenhouse()

        seen_ids = {j.id for j in all_jobs}
        for job in self.fetch_hubmub():
            if job.id not in seen_ids:
                all_jobs.append(job)
                seen_ids.add(job.id)

        print(f"[Scraper] Found {len(all_jobs)} total jobs")
        return all_jobs
