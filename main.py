import asyncio
import logging
import sys
import aiofiles
import discord
import time
import json

from EventRecord import EventRecord
from config import (
    DATA_PATH,
    LOG_FILE_PATH,
    QUERY_INTERVAL,
    SITE_PATH,
    END_USER_PATH,
)


class Client(discord.Client):
    """
    Inherrits discord.Client and adds special methods.
    """

    async def main_loop(self):
        """
        The main loop of the program. Checks for updates in events in the interval specified by QUERY_INTERVAL
        """

        self.everyone_notified: bool = True

        while True:
            # Updates the records if everyone is up to speed with the current updates
            if self.everyone_notified:
                t0 = time.time()

                # Fetch the saved verion from file and an updated version from the api
                new, old = await self.get_new_and_old()

                newly_opened = EventRecord.get_newly_opened_events(old, new)
                new_events = EventRecord.get_new_events(old, new)
                new_sign_up_start = EventRecord.get_new_signup_start(old, new)

            # Self.everyone_notified gets set to False if new events are discovered
            if len(newly_opened) != 0:
                self.everyone_notified = False
                logging.info(
                    f"Newly opened events: {list(newly_opened.eventrecord.keys())}"
                )

            if len(new_events) != 0:
                self.everyone_notified = False
                logging.info(f"New events: {list(new_events.eventrecord.keys())}")

            if len(new_sign_up_start) != 0:
                self.everyone_notified = False
                logging.info(
                    f"Newly changed sign-up start :{list(new_sign_up_start.eventrecord.keys())}"
                )

            # Notifies users if everyone is not up to speed
            if not self.everyone_notified:
                result_new = await client.notify_users_new(new_events)
                result_newly_opened = await client.notify_users_newly_opened(
                    newly_opened
                )
                result_new_signup_start = await client.notify_users_new_sign_up_start(
                    new_sign_up_start
                )

                # Sets self.everyone_notified to True if all functions ran without issue
                self.everyone_notified = all(
                    (result_new, result_newly_opened, result_new_signup_start)
                )

            if self.everyone_notified:
                # Save the new EventRecord
                await EventRecord.combine(old, new).save_to_json(DATA_PATH)

                await asyncio.sleep(QUERY_INTERVAL - (time.time() - t0))
            else:
                # Waits 500ms before retrying
                await asyncio.time.sleep(0.5)

    async def get_new_and_old(self) -> tuple[EventRecord, EventRecord]:
        """
        Gets an old EventRecord from disk, and a new EventRecord from the API
        """
        new = await EventRecord.get_updated()
        old = await EventRecord.from_json(DATA_PATH)
        logging.info("Fetched a new EventRecord")

        return new, old

    async def load_end_users(self, path: str) -> set[int]:
        """
        Loads users from a JSON file specified with path.
        The JSON file contains a list of user ids.
        """
        try:
            with open(path, "r") as f:
                user_ids: list[int] = json.load(f)
            self.end_users: list[discord.User] = list()
            for user_id in user_ids:
                user = await client.fetch_user(user_id)
                if user is not None:
                    self.end_users.append(user)
        except FileNotFoundError:
            self.end_users: list[discord.User] = list()

        logging.info(f"Loaded {len(self.end_users)} end users")

    async def append_end_user(self, path: str, user: discord.User):
        """
        Adds a user to the user register and saves it to a given path.
        """
        if user not in self.end_users:
            self.end_users.append(user)
            logging.info(f"User '{user}' added.")
            asyncio.create_task(self.save_end_users(path))

    async def remove_end_user(self, path: str, user: discord.User) -> None:
        """
        Removes a user form the user register and saves it to a given path.
        """
        if user in self.end_users:
            self.end_users.remove(user)
            logging.info(f"User '{user}' removed.")
            asyncio.create_task(self.save_end_users(path))

    async def save_end_users(self, path: str) -> None:
        """
        Saves the user regisrer to a given path as a list of user ids.
        """
        users = [user.id for user in self.end_users]
        async with aiofiles.open(path, "w") as f:
            f.write(json.dumps(users))

    async def notify_users_new(self, new_events: EventRecord) -> bool:
        """
        Notifies users of new events. Returns True if successfull and False if not.
        """
        for event in new_events.eventrecord.values():

            # Sets message according to event status
            if event.status == "CLOSED":
                message = (
                    f"Nytt arrangement lagt ut ({event.title}): {SITE_PATH}{event.id}/\n"
                    f"Påmeldingen starter {event.signup_start}."
                )
            elif event.status == "ACTIVE":
                message = f"Nytt arrangement åpnet påmelding ({event.title}): {SITE_PATH}{event.id}/"
            elif event.status == "TBA":
                message = (
                    f"Nytt arrangement lagt ut ({event.title}): {SITE_PATH}{event.id}/\n"
                    f"Detaljene er ennå ikke annonsert. Påmelding starter angivelig {event.signup_start}"
                )
            elif event.status == "NO_SIGNUP":
                message = (
                    f"Nytt arrangement lagt ut ({event.title}): {SITE_PATH}{event.id}/\n"
                    f"Arrangementet krever ikke påmelding."
                )
            # Continues loop if event status does not match anything to avoid endless
            # loops due to errors because of messange not beeing defined.
            else:
                logging.warning(
                    f"Event with id {event.id} does not have a valid status [status: '{event.status}']"
                )
                continue

            # Sends the message to each registered user
            for user in self.end_users:
                try:
                    await user.send(message)

                # Something went wrong
                except Exception as e:
                    logging.warning(
                        f"Somethng unexpected happened while notifying users of newly opened events: '{e}'"
                    )
                    return False

                logging.debug(
                    f"Messaged user {user} about newly added {event.status} event"
                )

        return True

    async def notify_users_newly_opened(self, new_events: EventRecord) -> bool:
        """
        Sends a message to every registered user with newly opened events.
        """
        for user in self.end_users:
            for event in new_events.eventrecord.values():
                try:
                    await user.send(
                        f"Nytt event åpnet påmelding ({event.title}): {SITE_PATH}{event.id}/"
                    )

                # Something bad happened
                except Exception as e:
                    logging.warning(
                        f"Somethng unexpected happened while notifying users of newly opened events: '{e}'"
                    )
                    return False

                logging.debug(
                    f"Messaged user {user} about newly added {event.status} event"
                )

        # Loop ran wihout problem
        return True

    async def notify_users_new_sign_up_start(self, new_events: EventRecord) -> bool:
        """
        Sends a message to every registered user with newly opened events.
        """
        for user in self.end_users:
            for event in new_events.eventrecord.values():
                try:
                    await user.send(
                        f"Et event endret når påmeldingen åpner ({event.title}): {SITE_PATH}{event.id}/"
                        f"Arrangementet åpner nå påmeldingen {event.signup_start}"
                    )

                # Something bad happened
                except Exception as e:
                    logging.warning(
                        f"Somethng unexpected happened while notifying users of newly changed events: '{e}'"
                    )
                    return False

                logging.debug(
                    f"Messaged user {user} about newly added {event.status} event"
                )

        # Loop ran wihout problem
        return True


# Initialized client
client = Client()


@client.event
async def on_ready():
    await client.load_end_users(END_USER_PATH)
    logging.info(f"Logged in as {client.user}")
    asyncio.create_task(client.main_loop())


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    # Adds user if user writtes start, and removes user if user writes slutt.
    logging.debug(f"Recived message from {message.author}")
    if message.content == "start":
        logging.debug(f"Recived 'start' from {message.author}")
        await client.append_end_user(END_USER_PATH, message.author)
        await message.reply("Bruker lagt til")
    elif message.content == "slutt":
        logging.debug(f"Recived 'slutt' from {message.author}")
        await client.remove_end_user(END_USER_PATH, message.author)
        await message.reply("Bruker fjernet")


if __name__ == "__main__":
    from dotenv import load_dotenv
    from os import environ

    # To remove RuntimeError on exit on windows as documented in this issue:
    # https://github.com/encode/httpx/issues/914
    if (
        sys.version_info[0] == 3
        and sys.version_info[1] >= 8
        and sys.platform.startswith("win")
    ):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    load_dotenv()

    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d [%(levelname)s]%(module)s.%(funcName)s:%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=logging.INFO,
        filename=LOG_FILE_PATH,
        encoding="utf8",
    )

    BOT_TOKEN = environ["BOT_TOKEN"]
    client.run(BOT_TOKEN)
