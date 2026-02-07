import os
import random

import discord

from pogbot.config import dir_path
from pogbot.utils import get_random_image_url
from pogbot.commands.audio import play_unmodified_audio_file


async def handle_pogcheck_message(message):
    pog_choice = random.randint(1, 10)
    msg = get_random_message(pog_choice)
    embed = discord.Embed(colour=discord.Colour.blue())
    embed.set_image(url=await get_random_image_url("pog", "lame", pog_choice))
    await message.channel.send(msg, embed=embed)


def get_random_message(val):
    low_rating = [
        f"Uh bro, you thought that was pog? It's only a {val} on the pogmeter!",
        f"Seriously bro that's so unpog! It's a {val} on the pogmeter!",
        f"Okay bro, you can pretend that was pog but its just a {val} on the pogmeter…",
    ]

    medium_rating = [
        f"Alright bro, I'll give it to you that's a {val} on the pogmeter",
        f"Gotta say that's pretty sweet bro, it's a {val} on the pogmeter.",
        f"Woah bro, that's a {val} on the pogmeter!",
    ]

    high_rating = [
        f"I never thought anything could be as pog as Chin…but that's a {val} on the pogmeter!",
        f"Dude…that's more pog than Bluffkin…its a {val} on the pogmeter!",
        f"Bro, seriously that's the most poggiest thing ever! Its a {val} on the pogmeter!",
    ]

    multi_rating = [
        f"Bro, can you believe that's like a {val} on the pogmeter?!",
        f"Bro listen! That's definitely a {val} on the pogmeter.",
        f"Alright bro, hear me out. That has got to be a {val} on the pogmeter.",
    ]

    chosen_list = (
        low_rating if val <= 4 else medium_rating if 4 < val < 7 else high_rating
    )
    chosen_list += multi_rating
    return random.choice(chosen_list)


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
!listen - Pogbot joins your voice channel and starts listening
!leave - Pogbot stops listening and leaves the voice channel
!say *message* - Anonymous TTS! DM this to Pogbot and it speaks in your voice channel (1 token)
!roast *@user* [context] - Anonymous AI roast! DM to Pogbot, it roasts them in voice (2 tokens)

Say "clip that" while Pogbot is listening to save the last 30s of audio!
```"""
    await message.channel.send(msg)
