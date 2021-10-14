import logging
import requests
from Event import Event
from HelperFunctions import check_status_code
import json
import concurrent.futures
from config import API_ENDPOINT, TEST_DATA_PATH


class EventRecord:
    """Used to hold a set of events"""

    def __init__(self):
        """
        Initializes a new empty EventRecord.
        Prints debug info if debug is True
        """
        self.eventrecord: dict[int, Event] = dict()

    def save_to_json(self, path: str) -> None:
        """
        Saves the eventrecord as a list of events to a given path
        """

        data = [event.to_json() for event in self.eventrecord.values()]
        with open(path, mode="w", encoding="utf8") as f:
            json.dump(data, f, ensure_ascii=False)

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
    def get_updated(cls, api_endpoint):
        """
        Gets an updated record of all events from the api endpoint
        """
        r = requests.get(api_endpoint)
        if not check_status_code(r):
            logging.warning(
                f"The request to {r.url} did not return with a response code starting with 2"
            )
            return cls.get_updated()

        result = cls()
        try:
            results: dict[str, any] = r.json()["results"]
            event_ids: list[int] = [event["id"] for event in results]
            with concurrent.futures.ThreadPoolExecutor() as ex:
                threads = [ex.submit(Event.get_event, (id)) for id in event_ids]
                result.eventrecord = {
                    thread.result().id: thread.result() for thread in threads
                }
        except KeyError as e:
            logging.critical(
                f"Something was from with the json returned from the request. KeyError: '{e}'"
            )
            raise e

        return result

    @classmethod
    def from_json(cls, path: str) -> None:
        """
        Creates a new EventRecord given a path to a json.
        The json should be a list of json-representations of events.
        """
        result = cls()

        try:
            with open(path, mode="r", encoding="utf8") as f:
                data = json.load(f)
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
        Gets the ids that are comon between two EventRecord objects
        """
        return set(eventrecord1.eventrecord.keys()) & set(
            eventrecord2.eventrecord.keys()
        )

    @classmethod
    def get_newly_opened_events(
        cls, old: "EventRecord", new: "EventRecord"
    ) -> "EventRecord":
        """
        Compares old and new and returnes a new EventRecord
        containing the events where events in old changed to
        "ACTIVE in new.
        """

        shared_ids = cls.shared_ids(old, new)

        newly_opened = cls()
        for id in shared_ids:
            if (
                old.get_event(id).status != "ACTIVE"
                and new.get_event(id).status == "ACTIVE"
            ):
                newly_opened.add_event(new.get_event(id).copy())

        logging.info(f"Found {len(newly_opened)} newly opened events")
        return newly_opened

    @classmethod
    def get_new_events(cls, old: "EventRecord", new: "EventRecord") -> "EventRecord":
        """
        Returns a new EventRecord that contains all the events
        that are unique to new.
        """
        shared_ids = cls.shared_ids(old, new)

        result = cls()
        new_ids = [id for id in new.eventrecord.keys() if id not in shared_ids]
        for id in new_ids:
            result.add_event(new.get_event(id).copy())

        logging.info(f"Found {len(result)} new events")
        return result

    @classmethod
    def combine(cls, old: "EventRecord", new: "EventRecord") -> "EventRecord":
        """
        Returns an updated EventRecord. Using an old EventRecord and a new EventRecord.
        All the events in old not in new is changed to expired and all the events in new is returned "as-is"
        """
        shared_ids = cls.shared_ids(old, new)

        combined = cls()
        for id in old.eventrecord.keys():
            if id not in shared_ids:
                event = old.get_event(id).copy()
                event.status = "EXPIRED"
                combined.add_event(event)
        for event in new.eventrecord.values():
            combined.add_event(event.copy())
        return combined


if __name__ == "__main__":
    # e = EventRecord.get_updated(API_ENDPOINT)
    # e.save_to_json(TEST_DATA_PATH)
    # e = EventRecord.from_json(TEST_DATA_PATH)
    # print(e)

    old = EventRecord.from_json(TEST_DATA_PATH)
    print("\nOld:")
    print(old)
    new = EventRecord.get_updated(API_ENDPOINT)
    print("\nNew:")
    print(new)
    print("\nNew events:")
    print(EventRecord.get_new_events(old, new))
    print("\nNewly opened:")
    print(EventRecord.get_newly_opened_events(old, new))
    print("\nCombined:")
    print(EventRecord.combine(old, new))
    pass
