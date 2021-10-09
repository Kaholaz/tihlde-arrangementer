import asyncio
from EventRecord import EventRecord
import json
from config import DATA_PATH, QUERY_INTERVAL, SITE_PATH, END_USER_PATH
import discord
import threading
import time


class Client(discord.Client):
    """
    Inherrits discord.Client and adds special methods.
    """

    async def main_loop(self):
        """
        The main loop of the program. Checks for updates in events in the interval specified by QUERY_INTERVAL
        """
        while True:
            t0 = time.time()
            new_events = EventRecord()
            thread = threading.Thread(target=update, args=[new_events])
            thread.start()
            while thread.is_alive():
                await asyncio.sleep(2)
            await client.notify_users(new_events)
            await asyncio.sleep(QUERY_INTERVAL - (time.time() - t0))

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

    async def append_end_user(self, path: str, user: discord.User):
        """
        Adds a user to the user register and saves it to a given path.
        """
        if user not in self.end_users:
            self.end_users.append(user)
            asyncio.create_task(self.save_end_users(path))

    async def remove_end_user(self, path: str, user: discord.User) -> None:
        """
        Removes a user form the user register and saves it to a given path.
        """
        if user in self.end_users:
            self.end_users.remove(user)
            asyncio.create_task(self.save_end_users(path))

    async def save_end_users(self, path: str) -> None:
        """
        Saves the user regisrer to a given path as a list of user ids.
        """
        users = [user.id for user in self.end_users]
        with open(path, "w") as f:
            json.dump(users, f)

    async def notify_users(self, new_events: EventRecord):
        """
        Sends a message to every registered user with new events.
        """
        for user in self.end_users:
            for event in new_events.eventrecord.values():
                await user.send(
                    f"Nytt event åpnet påmelding ({event.name}): {SITE_PATH}{event.id}/"
                )


# Initialized client
client = Client()


@client.event
async def on_ready():
    await client.load_end_users(END_USER_PATH)
    print(f"Logged in as {client.user}")
    asyncio.create_task(client.main_loop())


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    # adds user if user writtes start, and removes user if user writes slutt.
    if message.content == "start":
        await client.append_end_user(END_USER_PATH, message.author)
        await message.reply("Bruker lagt til")
    elif message.content == "slutt":
        await client.remove_end_user(END_USER_PATH, message.author)
        await message.reply("Bruker fjernet")


def update(result: EventRecord):
    """
    Checks for new events and saves an updated register to file.
    The method mutates result instead of giving a return value.
    This is because the method is designed to be run with the threading module.
    """
    old = EventRecord.from_json(DATA_PATH)

    new = EventRecord.from_url(SITE_PATH)

    newly_opened = EventRecord.get_newly_opened_events(old, new)

    for event in newly_opened.eventrecord.values():
        result.add_event(event)

    EventRecord.combine(old, new).save_to_json(DATA_PATH)


if __name__ == "__main__":
    from dotenv import load_dotenv
    from os import environ

    load_dotenv()

    BOT_TOKEN = environ["BOT_TOKEN"]
    client.run(BOT_TOKEN)
    asyncio.create_task(client.main_loop())
