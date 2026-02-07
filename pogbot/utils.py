import json

import aiohttp

from pogbot.config import GIPHY_API_KEY


def split_into_chunks(inp, sep="\n", limit=2000):
    ray = inp.split(sep)
    result = []
    temp = []
    for item in ray:
        cur_len = len("\n".join(temp))
        if cur_len + len(item) + 1 < limit:
            temp.append(item)
        else:
            result.append("\n".join(temp))
            temp = [item]
    if len(temp) > 0:
        result.append("\n".join(temp))
    return result


async def get_random_image_url(high_word, low_word, score):
    keyword = high_word if score > 5 else low_word
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"http://api.giphy.com/v1/gifs/random?tag={keyword}&api_key={GIPHY_API_KEY}"
        ) as response:
            data = json.loads(await response.text())
    return data["data"]["images"]["original"]["url"]
