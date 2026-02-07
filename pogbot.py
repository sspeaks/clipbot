#!/usr/bin/env python
import os
import json
import random
import re
import tempfile
import asyncio
from dataclasses import dataclass, asdict, field
from datetime import datetime

import discord
import aiohttp
import numpy
import openai
from azure.identity import DefaultAzureCredential
from azure.data.tables import TableServiceClient, UpdateMode
from azure.storage.blob import BlobServiceClient

print(os.environ["LD_LIBRARY_PATH"])
os.environ["LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH"]


@dataclass
class TokenUsage:
    RowKey: str
    PartitionKey: str = field(default_factory=lambda: str(datetime.now().timestamp()))
    tokens: int = 1
    tokensSpent: int = 0
    giftedTokens: int = 50
    last_usage: float = 1669190400.0


try:
    table_account_url = "https://pogbot.table.core.windows.net/"
    blob_account_url = "https://pogbot.blob.core.windows.net/"
    default_credential = DefaultAzureCredential()

    tableService = TableServiceClient(
        endpoint=table_account_url, credential=default_credential
    )
    blobService = BlobServiceClient(blob_account_url, credential=default_credential)

    container_name = "dalleimages"
    table_name = "tokenUsages"
    try:
        tableService.create_table(table_name)
        print("Table created!")
        blobService.create_container(container_name)
    except Exception as e:
        pass
    table_client = tableService.get_table_client(table_name=table_name)

except Exception as ex:
    print("Exception:")
    print(ex)
    exit()

dir_path = open(os.getenv("ASSETS_PATH"), "r").read()
TOKEN = open(os.getenv("DISCORD_TOKEN"), "r").read()
GUILD = os.getenv("DISCORD_GUILD")
GIPHY_API_KEY = open(os.getenv("GIPHY_API_KEY"), "r").read()
OPEN_AI_API = open(os.getenv("OPEN_AI_KEY"), "r").read()

openai.api_key = OPEN_AI_API

intents = discord.Intents.default()
intents.message_content = True
CLIENT = discord.Client(intents=intents)
discord.opus.load_opus("libopus.so")


def upload_image_to_container(filepath, blob_name):
    blob_client = blobService.get_blob_client(container=container_name, blob=blob_name)

    with open(file=filepath, mode="rb") as data:
        blob_client.upload_blob(data)


@CLIENT.event
async def on_connect():
    print("CONNECTED!")
    print(CLIENT.guilds)


@CLIENT.event
async def on_ready():
    for guild in CLIENT.guilds:
        if guild.name == GUILD:
            print(
                f"{CLIENT.user} is connected to the following guild:\n"
                f"{guild.name}(id: {guild.id})"
            )
            break


COMMANDS = {
    "!pogcheck": lambda msg: handle_pogcheck_message(msg),
    "!pogmedaddy": lambda msg: play_pog_file(msg),
    "!help": lambda msg: print_help_message(msg),
    "!bettermage": lambda msg: process_better_mage(msg),
    "!files": lambda msg: process_get_files(msg),
    "!playclip": lambda msg: play_file(msg, get_updated_tokens_for_user(msg.author)),
    "!tokens": lambda msg: process_tokens_command(msg, get_updated_tokens_for_user(msg.author)),
    "!chat": lambda msg: process_chat_command(msg),
    "!image": lambda msg: process_image_command(msg),
}


@CLIENT.event
async def on_message(message):
    if message.author == CLIENT.user:
        return

    if re.search("pog", message.content, flags=re.IGNORECASE):
        await message.add_reaction("<:mentos:1044740202947678228>")

    # !files only works in DMs
    if message.content == "!files" and re.search("^Direct Message", str(message.channel)):
        await process_get_files(message)
        return

    # Channel-restricted commands
    command = message.content.split()[0] if message.content else ""
    if command in COMMANDS:
        if command in ("!image",) or str(message.channel) == "poggers":
            await COMMANDS[command](message)


async def process_image_command(message):
    m = re.search(r"^!image\s+(.+)", message.content)
    query = m.group(1) if m else message.content

    response = openai.Image.create(prompt=query, n=1, size="1024x1024")
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

    completion = openai.ChatCompletion.create(
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


def split_into_chunks(inp, sep="\n", limit=2000):
    ray = inp.split(sep)

    result = []

    temp = []
    for item in ray:
        curLen = len("\n".join(temp))
        if curLen + len(item) + 1 < limit:
            temp.append(item)
        else:
            result.append("\n".join(temp))
            temp = [item]
    if len(temp) > 0:
        result.append("\n".join(temp))
    return result


async def process_tokens_command(message, tokens):
    await message.channel.send(
        f"You're a big nerd and have {tokens} left!! <:mentos:1044740202947678228>"
    )


async def play_file(message, tokens):
    if tokens < 1:
        await message.channel.send(
            f"You have {tokens} tokens left and can't play a clip <:mentos:1044740202947678228>"
        )
    else:
        m = re.search(r"^!playclip\s+(.+)", message.content)
        if m:
            file_name = m.group(1)
            audio_path = os.path.join(dir_path, "assets", "audio")
            choices = os.listdir(audio_path)
            if file_name in choices:
                if await play_unmodified_audio_file(
                    message, os.path.join(audio_path, file_name)
                ):
                    remove_one_token_from_user(message.author)
                    await message.channel.send(
                        f"File played! You have {tokens - 1} tokens left. You'll get another one in a week!"
                    )
            else:
                await message.channel.send(
                    f"'{file_name}' is not a valid file. To see a list of files, type !files in a private message with Pogbot"
                )
        else:
            await message.channel.send("You need to type !playclip {filename}")


def get_entity_from_user(user):
    user_filter = f"RowKey eq '{user.name}'"
    entities = list(table_client.query_entities(user_filter))
    entity = None
    if len(entities) != 1:
        entity = TokenUsage(RowKey=user.name)
    else:
        [temp_entity] = entities
        entity = TokenUsage(**dict(temp_entity))
    return entity


def remove_one_token_from_user(user):
    entity = get_entity_from_user(user)
    if entity.giftedTokens > 0:
        entity.giftedTokens -= 1
    else:
        entity.tokens -= 1
        entity.tokensSpent += 1
    update_entity(entity)


def update_entity(entity):
    table_client.upsert_entity(mode=UpdateMode.REPLACE, entity=asdict(entity))


def get_updated_tokens_for_user(user):
    entity = get_entity_from_user(user)
    old_usage = datetime.fromtimestamp(entity.last_usage)
    new_usage = datetime.now()
    weeks = (new_usage - old_usage).days // 7
    total_tokens = entity.tokens + entity.tokensSpent
    if total_tokens <= weeks + 1:  # Less than or equal to so I can gift people tokens
        entity.tokens = (weeks + 1) - entity.tokensSpent
    update_entity(entity)
    return entity.tokens + entity.giftedTokens


async def process_get_files(message):
    header = (
        "The files are returned in descending order of date added (most recent are at the top).\n"
        "They are also sent in multiple batches because a discord message cannot exceed 2000 characters in length."
    )
    await message.channel.send(header)
    audio_path = os.path.join(dir_path, "assets", "audio")
    full_path_choices = [os.path.join(audio_path, item) for item in os.listdir(audio_path)]
    full_path_choices.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    path_len = len(audio_path) + 1
    choices = [x[path_len:] for x in full_path_choices]
    if sum(len(x) for x in choices) + len(choices) < 2000:
        await message.channel.send("\n".join(choices))
    else:
        message_items = []
        for i in range(0, len(choices)):
            choice = choices[i]
            if len("\n".join(message_items)) + 1 + len(choice) >= 2000:
                await message.channel.send("\n".join(message_items))
                message_items = [choice]
            else:
                message_items.append(choice)
        await message.channel.send("\n".join(message_items))


async def handle_pogcheck_message(message):
    pog_choice = random.randint(1, 10)
    msg = get_random_message(pog_choice)
    embed = discord.Embed(colour=discord.Colour.blue())
    embed.set_image(url=await get_random_image_url("pog", "lame", pog_choice))
    await message.channel.send(msg, embed=embed)


async def get_random_image_url(high_word, low_word, score):
    keyword = high_word if score > 5 else low_word
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"http://api.giphy.com/v1/gifs/random?tag={keyword}&api_key={GIPHY_API_KEY}"
        ) as response:
            data = json.loads(await response.text())
    return data["data"]["images"]["original"]["url"]


def get_random_message(val):
    low_rating = [
        f"Uh bro, you thought that was pog? It’s only a {val} on the pogmeter!",
        f"Seriously bro that’s so unpog! It’s a {val} on the pogmeter!",
        f"Okay bro, you can pretend that was pog but its just a {val} on the pogmeter…",
    ]

    medium_rating = [
        f"Alright bro, I’ll give it to you that’s a {val} on the pogmeter",
        f"Gotta say that’s pretty sweet bro, it’s a {val} on the pogmeter.",
        f"Woah bro, that’s a {val} on the pogmeter!",
    ]

    high_rating = [
        f"I never thought anything could be as pog as Chin…but that’s a {val} on the pogmeter!",
        f"Dude…that’s more pog than Bluffkin…its a {val} on the pogmeter!",
        f"Bro, seriously that’s the most poggiest thing ever! Its a {val} on the pogmeter!",
    ]

    multi_rating = [
        f"Bro, can you believe that’s like a {val} on the pogmeter?!",
        f"Bro listen! That’s definitely a {val} on the pogmeter.",
        f"Alright bro, hear me out. That has got to be a {val} on the pogmeter.",
    ]

    chosen_list = (
        low_rating if val <= 4 else medium_rating if 4 < val < 7 else high_rating
    )
    chosen_list += multi_rating
    return random.choice(chosen_list)


async def play_unmodified_audio_file(message, source_path):
    voice_channel = message.author.voice
    if voice_channel is not None:
        vc = await voice_channel.channel.connect()
        vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=source_path))
        while vc.is_playing():
            await asyncio.sleep(0.5)
        await vc.disconnect()
        return True
    else:
        await message.author.send(
            "You're not in a channel. Daddy can't pog people that aren't in a channel."
        )
        return False


async def play_pog_file(message):
    for vc in CLIENT.voice_clients:
        await vc.disconnect()
        await asyncio.sleep(0.5)
    audio_path = os.path.join(dir_path, "assets", "audio")
    choices = [os.path.abspath(os.path.join(audio_path, item)) for item in os.listdir(audio_path)]
    source_path = random.choice(choices)

    # Get speed/frequency multipliers
    sigma = 0.1
    mu = 1
    [speed_mult] = numpy.clip(numpy.random.normal(mu, sigma, 1), 0.5, 2)
    [frequency_mult] = numpy.clip(numpy.random.normal(mu, sigma, 1), 0.5, 2)

    voice_channel = message.author.voice
    if voice_channel is not None:
        vc = await voice_channel.channel.connect()
        vc.play(
            discord.FFmpegPCMAudio(
                executable="ffmpeg",
                source=source_path,
                options=f'-filter:a "atempo={1 / frequency_mult},asetrate=44100*{frequency_mult},atempo={speed_mult}"',
            )
        )
        while vc.is_playing():
            await asyncio.sleep(0.5)
        await vc.disconnect()
    else:
        await message.author.send(
            "You're not in a channel. Daddy can't pog people that aren't in a channel."
        )
    await message.delete()


async def process_better_mage(message):
    msg = get_random_mage_message()
    im_path = os.path.join(dir_path, "assets", "nolorra_better.png")
    audio_path = os.path.join(dir_path, "assets", "AndHisNameIs.mp3")
    file = discord.File(im_path)
    await message.channel.send(msg, file=file)
    await play_unmodified_audio_file(message, audio_path)


def get_random_mage_message():
    better_mage_message = [
        "Who's the better mage??? Isn't it obvious? Nolorra!!!",
        "Some say he quit playing mage because he was too damn good at it.... the legendary Nolorra, of course!",
        '"When you don\'t want to make other players feel consistently inadequate, sometimes you must give up great things" -- Daisy 2022',
        "If it's opposite day, the answer is Bluffkin. If it's not... well, you know",
    ]
    return random.choice(better_mage_message)


async def print_help_message(message):
    msg = """```
!pogcheck - Returns a pog rating along with a random gif.
!pogmedaddy - Plays an audio file from your favorite cast of characters.
!help - Displays this help text.
!playclip *filename* - Plays a specific clip for the cost of 1 token
!tokens - Tells you how many tokens you have!
!files - Lists clips that can be played with !playclip **MUST BE IN PRIVATE MESSAGE WITH POGBOT**
!chat *question* - Ask a question and get a response
!image *prompt* - Generate an AI image from a prompt
```"""
    await message.channel.send(msg)


CLIENT.run(TOKEN)

#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python38Packages.discordpy python38Packages.python-dotenv python38Packages.aiohttp python38Packages.pynacl ffmpeg
