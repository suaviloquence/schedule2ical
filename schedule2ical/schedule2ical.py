import datetime as dt
from dataclasses import dataclass
from enum import Enum, unique, nonmember
from typing import List
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup, Tag
from icalendar import Calendar, Event

UCSCTZ = ZoneInfo("America/Los_Angeles")

"""
await fetch("https://my.ucsc.edu/psc/csprd/EMPLOYEE/SA/c/SA_LEARNER_SERVICES.SSR_SSENRL_LIST.GBL?NavColl=true&ICAGTarget=start&ICAJAXTrf=true", {
    "credentials": "include",
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "iframe",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin"
    },
    "referrer": "https://my.ucsc.edu/psc/csprd/EMPLOYEE/SA/c/NUI_FRAMEWORK.PT_AGSTARTPAGE_NUI.GBL?CONTEXTIDPARAMS=TEMPLATE_ID%3aPTPPNAVCOL&scname=ADMN_ENROLLMENT&PTPPB_GROUPLET_ID=SCX_ENROLLMENT&CRefName=ADMN_NAVCOLL_4&PanelCollapsible=Y&AJAXTransfer=Y",
    "method": "GET",
    "mode": "cors"
});
"""

@unique
class Weekday(Enum):
    Monday = "Mo"
    Tuesday = "Tu"
    Wednesday = "We"
    Thursday = "Th"
    Friday = "Fr"
    # idk if these are right for sure, dont have any weekend classes :3
    Saturday = "Sa"
    Sunday = "Su"

    @nonmember
    def weekday(self):
        return {Weekday.Monday: 0, Weekday.Tuesday: 1, Weekday.Wednesday: 2,
                Weekday.Thursday: 3, Weekday.Friday: 4, Weekday.Saturday: 5,
                Weekday.Sunday: 6}[self]

@dataclass
class MeetingTime:
    # start time of meeting, e.g., 1:20pm
    start_time: dt.time

    # end time of meeting, e.g., 2:25pm
    end_time: dt.time

    # the weekday(s) this takes place on, e.g., [Monday]
    # or [Monday, Wednesday, Friday]
    weekdays: List[Weekday]

    def rrule(self, end_date: dt.datetime):
        days = [wd.value.upper() for wd in self.weekdays]
        until = vDateTime(end_date).to_ical()
        return f"FREQ=WEEKLY;INTERVAL=1;BYDAY={','.join(days)};UNTIL={until.decode()}"

@dataclass
class Course:
    # course code, e.g., CSE 101M
    code: str

    # course title, e.g., Math Thinking for CS
    # seems to be abbreviated on course page
    title: str

    # section code, e.g., 01 or 01B
    section: str

    # type of class meeting, e.g., Discussion or Lecture
    component: str

    # whether the class is waitlisted (True) or enrolled (False)
    # we ignore dropped classes (bc why would you want that on your schedule)
    waitlist: bool

    # course instructor, e.g., Daniel Fremont
    instructor: str

    # start date, e.g., 01/08/2024 - this is usually the date the quarter starts,
    # not necessarily the first day of this class
    start_date: dt.date

    # end date, e.g., 03/15/2024 - like above, this is the end day of the quarter,
    # not the last day of the class
    end_date: dt.date

    # room name: e.g. ClassroomUnit 002
    room: str

    # TODO: should this be a list?
    # meeting times, e.g., [Mon, Wed, Fri] @ 1:20pm-2:25pm
    meeting_time: MeetingTime

# helper function to parse a meeting time of the format:
# WkDyLs 11:40AM - 1:15PM
# assumes input is correct
def parse_time(s: str) -> MeetingTime:
    days, _, times = s.partition(" ")
    start, _, end = times.partition(" - ")

    weekdays = [Weekday(days[i:i+2]) for i in range(0, len(days), 2)]

    def parse(st: str) -> dt.time:
        ampm = st[-2:]
        hh, _, mm = st[:-2].partition(":")
        return dt.time(int(hh), int(mm), tzinfo=UCSCTZ)

    return MeetingTime(weekdays=weekdays, start_time=parse(start),
                       end_time=parse(end))



# helper function to parse a mm/dd/yyyy date
# assumes input is correct
def parse_date(s: str) -> dt.date:
    mm, dd, yyyy = s.split('/')
    return dt.date(int(yyyy), int(mm), int(dd))


# returns a list because one entry can have multiple courses (lecture + section)
def parse_course(table: Tag) -> List[Course]:
    title_tag = table.find('td', class_='PAGROUPDIVIDER')

    if title_tag is None: return []

    code, _, title = title_tag.text.partition(" - ")

    info_table = table.find('table', class_="PSGROUPBOX")
    if info_table is None: return []
    # so beautiful ^.^
    status = info_table("tr", recursive=False)[1]("tr")[2]("td")[0].text.strip()
    if status == "Dropped":
        print(f"Skipping dropped class: {code} - {title}")
        return []
    waitlist = status == "Waiting"

    courses = []
    for section_row in info_table("tr", recursive=False)[2]("tr")[2:]:
        info_tds = section_row("td", recursive=False)

        section      = info_tds[1].text.strip()
        component    = info_tds[2].text.strip()
        instructor   = info_tds[5].text.strip()
        start_date, _, end_date = info_tds[6].text.strip().partition(" - ")
        start_date   = parse_date(start_date)
        end_date     = parse_date(end_date)
        room         = info_tds[4].text.strip()
        meeting_time = parse_time(info_tds[3].text.strip())

        courses.append(Course(code=code, title=title, waitlist=waitlist,
                              section=section, component=component,
                              instructor=instructor, start_date=start_date,
                              end_date=end_date, room=room,
                              meeting_time=meeting_time))

    return courses


def get_html(cookie: str) -> str:
    with open('Class Schedule.sample.html', 'r') as fp:
        return fp.read()
        


def parse_schedule(html: str) -> List[Course]:
    soup = BeautifulSoup(html, "html.parser")

    return [course
            for table in soup.find_all('table', class_='PSGROUPBOXWBO')
            if table.find(class_='PAGROUPDIVIDER') is not None
            for course in parse_course(table)]  # inner loop (silly python)

def generate_schedule(courses: List[Course], cruzid) -> Calendar:
    cal = Calendar()

    cal.add("PRODID", "-//people.ucsc.edu/~mcarr35/schedule2ical//0.1.0//EN")
    cal.add("VERSION", "2.0")

    cal_start = None
    cal_end = None

    for course in courses:
        # no meeting times
        if not course.meeting_time.weekdays:
            continue

        if cal_start is None or cal_start > course.start_date:
            cal_start = course.start_date
        if cal_end is None or cal_end < course.end_date:
            cal_end = course.end_date

        start_dt = dt.combine(course.start_date, course.meeting_time.start_time)
        weekdays = [wd.weekday() for wd in course.meeting_time.weekdays]

        # we could optimize this but it is guaranteed to terminate after 7
        # iterations, so not super worth it
        while start_dt.weekday() not in weekdays:
            start_dt += dt.timedelta(days=1)

        # this would break on a multi day meeting but so would many other things
        end_dt = dt.combine(start_dt.date(), course.meeting_time.end_time)

        evt = Event()

        evt["UID"] = f"{course.code}-{course.section}-{start_dt.isoformat()}@{cruzid}"
        evt["DTSTART"] = start_dt
        evt["DTEND"] = end_dt
        evt["RRULE"] = course.meeting_time.rrule(dt.datetime.combine(
            course.end_date, dt.time(tzinfo=UCSCTZ)))

    return calendar

