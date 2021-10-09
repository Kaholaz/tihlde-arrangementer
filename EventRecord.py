from Event import Event
from HelperFunctions import get_domain, get_soup
import json
import concurrent.futures
from config import SITE_PATH, TEST_DATA_PATH, TEST_SITE_PATH


class EventRecord:
    """Used to hold a set of events"""

    def __init__(self, debug: bool = False):
        """
        Initializes a new empty EventRecord.
        Prints debug info if debug is True
        """
        self.debug: bool = debug
        self.eventrecord: dict[int, Event] = dict()

    def save_to_json(self, path: str) -> None:
        """
        Saves the eventrecord as a list of events to a given path
        """
        data = [event.to_dict() for event in self.eventrecord.values()]
        with open(path, mode="w", encoding="utf8") as f:
            json.dump(data, f, ensure_ascii=False)

    def add_event(self, event: Event):
        """
        Adds event to eventrecord
        """
        self.eventrecord[event.id] = event

    def __str__(self):
        return "\n".join(str(event) for event in self.eventrecord.values())

    def __len__(self):
        return len(self.eventrecord)

    @classmethod
    def from_url(cls, url: str, debug=False) -> None:
        """
        Creates a new EventRecord given a path
        """
        soup = get_soup(url, "MuiSelect-outlined")

        if debug:
            print("Site retrived")

        # liks is the a-tags with the events
        root = soup.find("div", {"class": "MuiContainer-root"})
        event_list = root.div.div.div
        links = event_list.find_all("a")

        domain = get_domain(url)

        result = cls(debug=debug)
        with concurrent.futures.ThreadPoolExecutor() as ex:
            threads = [
                ex.submit(Event.get_event, (domain + link["href"]), debug=debug)
                for link in links
            ]
            result.eventrecord = {
                thread.result().id: thread.result() for thread in threads
            }

        return result

    @classmethod
    def from_json(cls, path: str, debug=False) -> None:
        """
        Creates a new EventRecord given a path to a json.
        The json should be a list of json-representations of events.
        """
        result = cls(debug=debug)

        try:
            with open(path, mode="r", encoding="utf8") as f:
                data = json.load(f)
            for entry in data:
                result.add_event(Event(**entry))
        except FileNotFoundError:
            pass

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

    @staticmethod
    def get_newly_opened_events(
        old: "EventRecord", new: "EventRecord"
    ) -> "EventRecord":
        """
        Compares old and new and returnes a new EventRecord
        containing the events where the events changed to "ACTIVE"
        or the events are new and tagged as "ACTIVE"
        """

        shared_ids = EventRecord.shared_ids(old, new)

        debug = old.debug or new.debug
        newly_opened = EventRecord(debug=debug)
        for id, event in new.eventrecord.items():
            if id in shared_ids:
                if old.eventrecord[id].status != "ACTIVE" and event.status == "ACTIVE":
                    newly_opened.add_event(event.copy())
            else:
                if event.status == "ACTIVE":
                    newly_opened.add_event(event.copy())
        return newly_opened

    @staticmethod
    def combine(old: "EventRecord", new: "EventRecord") -> "EventRecord":
        """
        Returns an updated EventRecord. Using an old EventRecord and a new EventRecord.
        All the events in old not in new is changed to expired and all the events in new is returned "as-is"
        """
        shared_ids = EventRecord.shared_ids(old, new)
        debug = old.debug or new.debug

        combined = EventRecord(debug=debug)
        for id in old.eventrecord.keys():
            if id not in shared_ids:
                event = old.eventrecord[id].copy()
                event.status = "EXPIRED"
                combined.add_event(event)
        for event in new.eventrecord.values():
            combined.add_event(event.copy())
        return combined


if __name__ == "__main__":
    e = EventRecord.from_url(TEST_SITE_PATH, debug=True)
    e.save_to_json(TEST_DATA_PATH)
    e.from_json(TEST_DATA_PATH)
    print(e)

    old = EventRecord.from_json(TEST_DATA_PATH, debug=True)
    print(type(old))
    new = EventRecord.from_url(SITE_PATH, debug=True)
    print(type(new))
    print("\nNewly opened:")
    print(EventRecord.get_newly_opened_events(old, new))
    print("\nCombined:")
    print(EventRecord.combine(old, new))
