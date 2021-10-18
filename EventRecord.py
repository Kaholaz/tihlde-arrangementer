import asyncio
import logging
import sys
import aiohttp
import json
import aiofiles

from config import API_ENDPOINT
from Event import Event
from HelperFunctions import fetch_json


class EventRecord:
    """Used to hold a set of events"""

    def __init__(self):
        """
        Initializes a new empty EventRecord.
        Prints debug info if debug is True
        """
        self.eventrecord: dict[int, Event] = dict()

    async def save_to_json(self, path: str) -> None:
        """
        Saves the eventrecord as a list of events to a given path
        """

        data = [event.to_json() for event in self.eventrecord.values()]
        async with aiofiles.open(path, mode="w", encoding="utf8") as f:
            await f.write(json.dumps(data, ensure_ascii=False))

    def add_event(self, event: Event):
        """
        Adds event to eventrecord
        """
        self.eventrecord[event.id] = event

    def get_event(self, id: int):
        """
        Gets event given an event id
        """
        return self.eventrecord[id]

    def __str__(self):
        return "\n".join(str(event) for event in self.eventrecord.values())

    def __len__(self):
        return len(self.eventrecord)

    @classmethod
    async def get_updated(cls):
        """
        Gets an updated record of all events from the api endpoint
        """
        url = API_ENDPOINT

        async with aiohttp.ClientSession() as session:
            events_json = await fetch_json(session, url)

            result = cls()
            try:
                results: dict[str, any] = events_json["results"]
                event_ids: list[int] = [event["id"] for event in results]

                # Gets every event for every event_id async
                events = await asyncio.gather(
                    *(Event.get_event(session, event_id) for event_id in event_ids)
                )
                result.eventrecord = {event.id: event for event in events}

            # Bad JSON
            except KeyError as e:
                logging.critical(
                    f"Something was from with the json returned from the request [url: {url}]. KeyError: '{e}'"
                )
                raise e

        return result

    @classmethod
    async def from_json(cls, path: str) -> None:
        """
        Creates a new EventRecord given a path to a json.
        The json should be a list of json-representations of events.
        """
        result = cls()

        try:
            async with aiofiles.open(path, mode="r", encoding="utf8") as f:
                raw = await f.read()
            data = json.loads(raw)
            for entry in data:
                result.add_event(Event(**entry))
        except FileNotFoundError:
            logging.warning(f"File not found: {path}")

        return result

    @staticmethod
    def shared_ids(
        eventrecord1: "EventRecord", eventrecord2: "EventRecord"
    ) -> set[int]:
        """
        Gets the ids that are comon between two `EventRecord` instances
        """
        return set(eventrecord1.eventrecord.keys()) & set(
            eventrecord2.eventrecord.keys()
        )

    @classmethod
    def get_newly_opened_events(
        cls, old: "EventRecord", new: "EventRecord"
    ) -> "EventRecord":
        """
        Compares old and new and returnes a new `EventRecord`
        containing the events where events in old changed to
        "ACTIVE" in new.
        """

        shared_ids = cls.shared_ids(old, new)

        newly_opened = cls()
        for id in shared_ids:
            # If the event switched from anything but "ACTIVE" to "ACTIVE"
            if (
                old.get_event(id).status != "ACTIVE"
                and new.get_event(id).status == "ACTIVE"
            ):
                newly_opened.add_event(new.get_event(id).copy())

        logging.debug(f"Found {len(newly_opened)} newly opened events")
        return newly_opened

    @classmethod
    def get_new_events(cls, old: "EventRecord", new: "EventRecord") -> "EventRecord":
        """
        Returns a new `EventRecord` that contains all the events
        that are unique to new.
        """
        shared_ids = cls.shared_ids(old, new)

        result = cls()

        # All ids in new, but not in old
        new_ids = [id for id in new.eventrecord.keys() if id not in shared_ids]
        for id in new_ids:
            result.add_event(new.get_event(id).copy())

        logging.debug(f"Found {len(result)} new events")
        return result

    @classmethod
    def combine(cls, old: "EventRecord", new: "EventRecord") -> "EventRecord":
        """
        Returns an updated EventRecord. Using an old `EventRecord` and a new `EventRecord`.
        All the events in old not in new is changed to expired and all the events in new is returned "as-is"
        """
        shared_ids = cls.shared_ids(old, new)

        combined = cls()

        # All events in old that are not in new, gets set to "EXPIRED"
        for id in old.eventrecord.keys():
            if id not in shared_ids:
                event = old.get_event(id).copy()
                event.status = "EXPIRED"
                combined.add_event(event)

        # All events in new added as is
        for event in new.eventrecord.values():
            combined.add_event(event.copy())

        return combined


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
    from config import TEST_DATA_PATH

    # e = asyncio.run(EventRecord.get_updated())
    # asyncio.run(e.save_to_json(TEST_DATA_PATH))
    # e = asyncio.run(EventRecord.from_json(TEST_DATA_PATH))
    # print(e)

    # old = asyncio.run(EventRecord.from_json(TEST_DATA_PATH))
    # print("\nOld:")
    # print(old)
    # new = asyncio.run(EventRecord.get_updated())
    # print("\nNew:")
    # print(new)
    # print("\nNew events:")
    # print(EventRecord.get_new_events(old, new))
    # print("\nNewly opened:")
    # print(EventRecord.get_newly_opened_events(old, new))
    # print("\nCombined:")
    # print(EventRecord.combine(old, new))

    pass
