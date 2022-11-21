#!/user/bin/env python
import os
import json
import random
import discord
from dotenv import load_dotenv
from time import sleep
import aiohttp
import numpy

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
    if should_process_pogcheck_message(message):
        await handle_pogcheck_message(message)
    if should_process_pogmedaddy_message(message):
        await play_pog_file(message)
    if should_process_help_message(message):
        await print_help_message(message)
    if should_process_better_mage(message):
        await process_better_mage(message)


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
    if message.author == CLIENT.user:
        return False
    if message.content == "!bettermage":
        return True
    return False


async def process_better_mage(message):
    msg = "Who's the better mage??? Isn't it obvious? Nolorra!!!"
    im_path = dir_path + "/assets/nolorra_better.png"
    file = discord.File(im_path)
    await message.channel.send(msg, file=file)


async def print_help_message(message):
    msg = """
    ```
    !pogcheck - Returns a pog rating along with a random gif.
    !pogmedaddy - Plays an audio file from your favorite cast of characters.
    !help - Displays this help text.
    ```
    """
    await message.channel.send(msg)


CLIENT.run(TOKEN)

#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python38Packages.discordpy python38Packages.python-dotenv python38Packages.aiohttp python38Packages.pynacl ffmpeg
