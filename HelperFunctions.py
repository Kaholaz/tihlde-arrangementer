import logging
import aiohttp
import asyncio


async def fetch_json(
    session: aiohttp.ClientSession, url: str
) -> aiohttp.ClientResponse:
    """
    Retrives a json from a an api given the url
    """
    async with session.get(url) as r:
        if r.status != 200:
            logging.warning(
                f"The request to {r.url} did not return with a response code for OK [200]"
            )
            # Retrying
            await asyncio.sleep(0.5)
            return await fetch_json(session, id)
        else:
            return await r.json()
