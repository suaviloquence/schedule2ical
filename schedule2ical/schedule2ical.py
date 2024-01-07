from dataclasses import dataclass
from typing import List

import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event

@dataclass
class Course:
    ...

def parse_schedule(html: str) -> List[Course]:
    ...

def generate_schedule(courses: List[Course]) -> Calendar:
    ...

def run_cli():
    ...

if __name__ == '__main__':
    run_cli()
