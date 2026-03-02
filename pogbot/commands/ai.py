import asyncio
import re
import tempfile

import aiohttp
import discord
import openai

from pogbot.storage import blob_account_url, container_name, upload_image_to_container
from pogbot.utils import split_into_chunks


async def process_image_command(message):
    m = re.search(r"^!image\s+(.+)", message.content)
    query = m.group(1) if m else message.content

    response = await asyncio.to_thread(
        openai.Image.create, prompt=query, n=1, size="1024x1024"
    )
    image_url = response["data"][0]["url"]
    m = re.search(r"/([^\/]+?\.png)", image_url)
    if m:
        image_name = m.group(1)
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                img_data = await resp.read()
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(img_data)
            upload_image_to_container(tmp.name, image_name)
            image_url = f"{blob_account_url}{container_name}/{image_name}"

    embed = discord.Embed(colour=discord.Colour.blue())
    embed.set_image(url=image_url)
    await message.channel.send("", embed=embed)


async def process_chat_command(message):
    m = re.search(r"^!chat\s+(.+)", message.content)
    query = m.group(1) if m else message.content

    completion = await asyncio.to_thread(
        openai.ChatCompletion.create,
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant who tries to answer questions to the best of your ability.",
            },
            {"role": "user", "content": query},
        ],
    )
    content = completion.choices[0].message.content

    messages = split_into_chunks(content)
    for m in messages:
        await message.channel.send(m)
