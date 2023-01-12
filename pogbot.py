#!/usr/bin/env python
import os
import json
import random
import discord
from dotenv import load_dotenv
from time import sleep
import aiohttp
import numpy
import re
from azure.identity import DefaultAzureCredential
from azure.data.tables import TableServiceClient, UpdateMode
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class TokenUsage:
    RowKey: str
    PartitionKey: str = str(datetime.now().timestamp())
    tokens: int = 1
    tokensSpent: int = 0
    giftedTokens: int = 50
    last_usage: float = 1669190400.0


try:
    account_url = "https://pogbot.table.core.windows.net/"
    default_credential = DefaultAzureCredential()

    # Create the BlobServiceClient object
    service = TableServiceClient(endpoint=account_url, credential=default_credential)

    table_name = "tokenUsages"
    try:
        service.create_table(table_name)
        print("Table created!")
    except Exception as e:
        pass
    table_client = service.get_table_client(table_name=table_name)

except Exception as ex:
    print("Exception:")
    print(ex)
    exit()

dir_path = os.path.dirname(os.path.realpath(__file__))
print(dir_path)
load_dotenv()
print("loaded env")
TOKEN = os.getenv("DISCORD_TOKEN")
print(TOKEN)
GUILD = os.getenv("DISCORD_GUILD")
print(GUILD)
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")
print(GIPHY_API_KEY)

CLIENT = discord.Client()
# CLIENT = discord.Client(intents=discord.Intents.default())


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


@CLIENT.event
async def on_message(message):
    if message.author != CLIENT.user and re.search(
        "pog", message.content, flags=re.IGNORECASE
    ):
        await message.add_reaction("<:mentos:1044740202947678228>")
    if should_process_pogcheck_message(message):
        await handle_pogcheck_message(message)
        return
    if should_process_pogmedaddy_message(message):
        await play_pog_file(message)
        return
    if should_process_help_message(message):
        await print_help_message(message)
        return
    if should_process_better_mage(message):
        await process_better_mage(message)
        return
    if should_process_get_files(message):
        await process_get_files(message)
        return
    if should_process_play_file(message):
        await play_file(message, get_updated_tokens_for_user(message.author))
        return
    if should_process_tokens_command(message):
        await process_tokens_command(
            message, get_updated_tokens_for_user(message.author)
        )
        return


def should_process_tokens_command(message):
    if message.author == CLIENT.user:
        return False
    if str(message.channel) != "poggers":
        return False
    if re.search("!tokens", str(message.content)) is None:
        # print(message)
        return False
    return True


async def process_tokens_command(message, tokens):
    await message.channel.send(
        f"You're a big nerd and have {tokens} left!! <:mentos:1044740202947678228>"
    )


def should_process_play_file(message):
    if message.author == CLIENT.user:
        return False
    if str(message.channel) != "poggers":
        return False
    if re.search("!playclip", str(message.content)) is None:
        # print(message)
        return False
    return True


async def play_file(message, tokens):
    if tokens < 1:
        await message.channel.send(
            f"You have {tokens} tokens left and can't play a clip <:mentos:1044740202947678228>"
        )
    else:
        m = re.search("^!playclip\s+(.+)", message.content)
        if m:
            fileName = m.group(1)
            audioPath = dir_path + "/assets/audio"
            choices = list([item for item in os.listdir(audioPath)])
            if fileName in choices:
                if await play_unmodified_audio_file(
                    message, audioPath + "/" + fileName
                ):
                    remove_one_token_from_user(message.author)
                    await message.channel.send(
                        f"File played! You have {tokens - 1} tokens left. You'll get another one in a week!"
                    )
            else:
                await message.channel.send(
                    f"'{fileName}' is not a valid file. To see a list of files, type !files in a private message with Pogbot"
                )
        else:
            # await message.channel.send("You need to type !play \{filename\}")
            await message.channel.send("You need to type !playclip {filename}")


def should_process_get_files(message):
    if message.author == CLIENT.user:
        return False
    # Direct Message with Bloodfox610#8162
    if re.search("^Direct Message", str(message.channel)) is None:
        return False
    if message.content != "!files":
        return False
    return True


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
    header = """
The files are returned in descending order of date added (most recent are at the top).
They are also sent in multiple batches because a discord message cannot exceed 2000 characters in length.
	"""
    await message.channel.send(header)
    audioPath = dir_path + "/assets/audio"
    full_path_choice = [os.path.join(audioPath, item) for item in os.listdir(audioPath)]
    full_path_choice.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    path_len = len(audioPath) + 1
    choices = [x[path_len:] for x in full_path_choice]
    if sum(map(lambda x: len(x), choices)) + len(choices) < 2000:
        await message.channel.send(choices)
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
    session = aiohttp.ClientSession()
    keyword = high_word if score > 5 else low_word
    response = await session.get(
        f"http://api.giphy.com/v1/gifs/random?tag={keyword}&api_key={GIPHY_API_KEY}"
    )
    data = json.loads(await response.text())
    await session.close()
    return data["data"]["images"]["original"]["url"]


def should_process_pogcheck_message(message):
    if message.author == CLIENT.user:
        return False
    #    if message.channel.name != 'pogcheck':
    #       return False
    if message.content == "!pogcheck":
        return True
    return False


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


def should_process_pogmedaddy_message(message):
    if message.author == CLIENT.user:
        return False
    #  if message.channel.name != 'pogcheck':
    #     return False
    if message.content == "!pogmedaddy":
        return True
    return False


async def play_unmodified_audio_file(message, sourcePath):
    voice_channel = message.author.voice
    if voice_channel != None:
        vc = await voice_channel.channel.connect()
        vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=sourcePath))
        while vc.is_playing():
            sleep(0.5)
        await vc.disconnect()
        return True
    else:
        await message.author.send(
            "You're is not in a channel. Daddy can't pog people that aren't in a channel."
        )
        return False
    # Delete command after the audio is done playing.
    # await message.delete()


async def play_pog_file(message):
    for vc in CLIENT.voice_clients:
        vc.disconnect()
        sleep(0.5)
    audioPath = dir_path + "/assets/audio"
    choices = [
        os.path.abspath(audioPath + "/" + item) for item in os.listdir(audioPath)
    ]
    sourcePath = random.choice(choices)

    # Get speed/frequency multipliers
    sigma = 0.1
    mu = 1
    [speed_mult] = numpy.clip(numpy.random.normal(mu, sigma, 1), 0.5, 2)
    [frequency_mult] = numpy.clip(numpy.random.normal(mu, sigma, 1), 0.5, 2)

    voice_channel = message.author.voice
    if voice_channel != None:
        vc = await voice_channel.channel.connect()
        vc.play(
            discord.FFmpegPCMAudio(
                executable="ffmpeg",
                source=sourcePath,
                options=f'-filter:a "atempo='
                + str(1 / frequency_mult)
                + ",asetrate=44100*"
                + str(frequency_mult)
                + ",atempo="
                + str(speed_mult)
                + '"',
            )
        )
        while vc.is_playing():
            sleep(0.1)
        await vc.disconnect()
    else:
        await message.author.send(
            "You're is not in a channel. Daddy can't pog people that aren't in a channel."
        )
    # Delete command after the audio is done playing.
    await message.delete()


def should_process_help_message(message):
    if message.author == CLIENT.user:
        return False
    # if message.channel.name != 'pogcheck':
    #   return False
    if message.content == "!help":
        return True
    return False


def should_process_better_mage(message):
    # if message.author == CLIENT.user:
    #     return False
    if message.content == "!bettermage":
        return True
    return False


async def process_better_mage(message):
    msg = get_random_mage_message()
    im_path = dir_path + "/assets/nolorra_better.png"
    audioPath = dir_path + "/assets/AndHisNameIs.mp3"
    file = discord.File(im_path)
    await message.channel.send(msg, file=file)
    await play_unmodified_audio_file(message, audioPath)


def get_random_mage_message():
    better_mage_message = [
        "Who's the better mage??? Isn't it obvious? Nolorra!!!",
        "Some say he quit playing mage because he was too damn good at it.... the legendary Nolorra, of course!",
        '"When you don\'t want to make other players feel consistently inadequate, sometimes you must give up great things" -- Daisy 2022',
        "If it's opposite day, the answer is Bluffkin. If it's not... well, you know",
    ]
    return random.choice(better_mage_message)


async def print_help_message(message):
    msg = """
	```
	!pogcheck - Returns a pog rating along with a random gif.
	!pogmedaddy - Plays an audio file from your favorite cast of characters.
	!help - Displays this help text.
	!playclip *filename* - Plays a specific clip for the cost of 1 token
	!tokens - Tells you how many tokens you have!
	!files - Lists clips that can be played with !playclip **MUST BE IN PRIVATE MESSAGE WITH POGBOT**

	```
	"""
    await message.channel.send(msg)


CLIENT.run(TOKEN)

#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python38Packages.discordpy python38Packages.python-dotenv python38Packages.aiohttp python38Packages.pynacl ffmpeg
