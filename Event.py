import datetime
from typing import Type
from bs4 import BeautifulSoup
from HelperFunctions import get_soup
import re


class Event:
    MONTHS = {
        "jan": 1,
        "feb": 2,
        "mars": 3,
        "april": 4,
        "mai": 5,
        "juni": 6,
        "juli": 7,
        "aug": 8,
        "sep": 9,
        "okt": 10,
        "nov": 11,
        "des": 12,
    }

    def __init__(
        self,
        id: int,
        name: str,
        start: str,
        end: str,
        deadline: str,
        place: str,
        status: str,
    ):
        """
        Creates a new Event given a set of parameters
        """
        self.id = id
        self.name = name
        self.start = datetime.datetime.fromisoformat(start)
        self.end = datetime.datetime.fromisoformat(end)
        if deadline is None:
            self.deadline = None
        else:
            self.deadline = datetime.datetime.fromisoformat(deadline)
        self.place = place
        self.status = status

    @classmethod
    def get_event(cls, url: str, debug=False) -> Type["Event"]:
        """
        Returns a new event given a url to an event
        """
        soup = get_soup(url, "MuiButton-outlined")

        id = cls.get_id(url)
        name = cls.get_name(soup)

        root = soup.find("div", {"class": "MuiContainer-root"})
        side = root.div.div  # the info on the left side
        boxes = side.find_all("div")  # all divs in the side-info
        details = boxes[0]

        start_str, end_str, place = cls.get_info(details)

        deadline_str, status = cls.get_deadline_and_status(side, end_str)

        if debug:
            print(f"Event: {name} initialized")

        return cls(id, name, start_str, end_str, deadline_str, place, status)

    @staticmethod
    def get_id(url: str) -> int:
        """Gets the id of an event given a url"""
        result = re.search(r"(?:arrangementer/)(\d+)", url).groups()[0]
        id = int(result)
        return id

    @staticmethod
    def get_name(soup: BeautifulSoup) -> str:
        """Gets the name of an event given a html document"""
        pattern = r".+(?= · TIHLDE)"
        title_raw = soup.find("title").text

        name = re.search(pattern, title_raw).group(0)
        return name

    @classmethod
    def get_info(cls, details: BeautifulSoup) -> tuple[str, str, str]:
        """Gets the start, end and place of an event"""
        info = details.find_all("h6")
        start_str: str = cls.parse_datetime(info[0].text)
        end_str: str = cls.parse_datetime(info[1].text)
        place: str = info[2].text[7:]
        return start_str, end_str, place

    @classmethod
    def get_deadline_and_status(
        cls, side: BeautifulSoup, end_str: str
    ) -> tuple[str, str]:
        """Gets a deadline and current status of an event"""
        status = None
        if datetime.datetime.now() > datetime.datetime.fromisoformat(end_str):
            status = "EXPIRED"

        boxes = side.find_all("div")
        if len(boxes) == 1:
            deadline_str = None
            if status is None:
                status = "NO SIGNUP"
        else:
            sign_up = boxes[1]
            try:
                deadline_raw = sign_up.find_all("h6")[2].text
                deadline_str = cls.parse_datetime(deadline_raw)
                if status is None:
                    if len(side.find_all("a")) == 2:
                        status = "ACTIVE"
                    else:
                        status = "CLOSED"
            except IndexError:
                deadline_str = None
                if status is None:
                    status = "CLOSED"

        return deadline_str, status

    @classmethod
    def parse_datetime(cls, datetime_str: str) -> str:
        """Gets the datetime of a formatted date in the event and returns a iso-formatted datetime string"""
        pattern = r"\w+\. (?P<day>\d+) (?P<month>\w+)\s?(?P<year>\d+)?( - kl. (?P<hours>\d+):(?P<minutes>\d+))?"
        result = re.search(
            pattern,
            datetime_str,
        )
        groupdict = result.groupdict()

        day = int(groupdict["day"])
        month = cls.MONTHS[(groupdict["month"])]

        if groupdict["year"] is not None:
            year = int(groupdict["year"])
        else:
            year = datetime.date.today().year

        if groupdict["hours"] is not None:
            hours = int(groupdict["hours"])
            minutes = int(groupdict["minutes"])
            return datetime.datetime(year, month, day, hours, minutes).isoformat()
        else:
            return datetime.datetime(year, month, day).isoformat()

    def to_dict(self) -> dict:
        """Returns a dict representation of an event"""
        return {
            "id": self.id,
            "name": self.name,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "deadline": None if self.deadline is None else self.deadline.isoformat(),
            "place": self.place,
            "status": self.status,
        }

    def copy(self) -> "Event":
        return self.__class__(**self.to_dict())

    def __repr__(self):
        return (
            f"{type(self).__name__}("
            f"id={self.id}, start={self.start.isoformat()}, "
            f"name={self.name}, "
            f"end={self.end.isoformat()}, "
            f"deadline={None if self.deadline is None else self.deadline.isoformat()}, "
            f"place={self.place}, "
            f"status={self.status})"
        )


if __name__ == "__main__":
    print(
        Event.get_event(
            "https://dev.tihlde.org/arrangementer/5/17-mai-pamelding-stengt/"
        )
    )
