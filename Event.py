import asyncio
import datetime
import sys
from typing import Literal
import aiohttp
import logging

from HelperFunctions import fetch_json
from config import API_ENDPOINT


class Event:
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
            # Converts all date fields to a string representation
            if type(value) == datetime.datetime:
                result_json[key] = value.isoformat()
        return result_json

    @classmethod
    async def get_event(cls, session: aiohttp.ClientSession, id: int) -> "Event":
        url = f"{API_ENDPOINT}{id}"
        event_json = await fetch_json(session, url)

        # Bad response
        # Event(id) creates an event where id is the value of id and all other fields are set to None
        if len(event_json) == 1:
            logging.warning(
                f"The request to evnt with url {url} had a response with length 1"
            )
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

        # Bad JSON
        except KeyError as e:
            logging.warning(
                f"Something was from with the json returned from the request [url: {url}]. KeyError: '{e}'"
            )
            return Event(id)

        # Creating new event with the fetched parameters
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
        logging.debug(f"Event with id {event.id} retrived")
        return event

    def copy(self) -> "Event":
        logging.debug(f"Copied event with id: {self.id}")
        return self.__class__(**self.to_json())

    def __repr__(self):
        logging.debug(f"Returned string representation of event with id: {self.id}")

        # Copies dict to no make changes to the object (mutable)
        result_dict = self.__dict__.copy()

        # Datetimes converted into equivalent iso-formatted strings
        for key, value in result_dict.items():
            if type(value) == datetime.datetime:
                result_dict[key] = value.isoformat()

        # Formatted as you would call the function
        return f"{type(self).__name__}({', '.join(f'{key}={value}' for key, value in result_dict.items())})"


if __name__ == "__main__":
    # To remove RuntimeError on exit on windows as documented in this issue:
    # https://github.com/encode/httpx/issues/914
    if (
        sys.version_info[0] == 3
        and sys.version_info[1] >= 8
        and sys.platform.startswith("win")
    ):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Troubleshooting:

    async def main():
        # async with aiohttp.ClientSession() as session:
        #     print(await Event.get_event(session, 277))
        return

    # logging.basicConfig(filename="test.log", level=logging.DEBUG)

    asyncio.run(main())
