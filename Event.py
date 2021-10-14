import datetime
from typing import Literal
import requests
import logging
from HelperFunctions import check_status_code
from config import API_ENDPOINT


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
        title: str = None,
        start: str = None,
        end: str = None,
        deadline: str = None,
        signup_start: str = None,
        place: str = None,
        status: Literal["EXPIRED", "CLOSED", "ACTIVE", "NO_SIGNUP", "TBA"] = None,
    ):
        """
        Creates a new Event given a set of parameters
        """
        self.id = id
        self.title = title
        self.start = datetime.datetime.fromisoformat(start)
        self.end = datetime.datetime.fromisoformat(end)
        self.deadline = datetime.datetime.fromisoformat(deadline)
        self.signup_start = datetime.datetime.fromisoformat(signup_start)
        self.place = place
        self.status = status

    def to_json(self) -> dict:
        """Returns a dict representation of an event"""
        logging.debug(f"Convertet event with id: {self.id}, to dict")
        result_json = self.__dict__.copy()
        for key, value in result_json.items():
            if type(value) == datetime.datetime:
                result_json[key] = value.isoformat()
        return result_json

    @classmethod
    def get_event(cls, id: int) -> "Event":
        r = requests.get(f"{API_ENDPOINT}{id}")
        if not check_status_code(r):
            logging.warning(
                f"The request to {r.url} did not return with a response code starting with 2"
            )
            return Event(id)

        event_json = r.json()
        if len(r.json()) == 1:
            logging.warning(f"The request to {r.url} had a response with length 1")
            return Event(id)

        try:
            title = event_json["title"]
            start_datetime = event_json["start_date"]
            end_datetime = event_json["end_date"]
            deadline = event_json["end_registration_at"]
            signup_start = event_json["start_registration_at"]
            place = event_json["location"]

            if event_json["expired"]:
                status = "EXPIRED"
            elif event_json["closed"]:
                status = "CLOSED"
            elif event_json["sign_up"]:
                status = "ACTIVE"
            elif event_json["description"] == "TBA":
                status = "TBA"
            else:
                status = "NO_SIGNUP"
        except KeyError as e:
            logging.warning(
                f"Something was from with the json returned from the request. KeyError: '{e}'"
            )
            return Event(id)

        event = Event(
            id=id,
            title=title,
            start=start_datetime,
            end=end_datetime,
            deadline=deadline,
            signup_start=signup_start,
            place=place,
            status=status,
        )
        logging.debug(f"Event with id {event.id} retrived from {r.url}")
        return event

    def copy(self) -> "Event":
        logging.debug(f"Copied event with id: {self.id}")
        return self.__class__(**self.to_json())

    def __repr__(self):
        logging.debug(f"Returned string representation of event with id: {self.id}")
        return (
            f"{type(self).__name__}("
            f"id={self.id}, "
            f"title={self.title}, "
            f"start={self.start.isoformat()}, "
            f"end={self.end.isoformat()}, "
            f"deadline={self.deadline.isoformat()}, "
            f"signup_start={self.signup_start.isoformat()}, "
            f"place={self.place}, "
            f"status={self.status})"
        )


if __name__ == "__main__":
    logging.basicConfig(filename="test.log", level=logging.DEBUG)
    print(Event.get_event(277))
